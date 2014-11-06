# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 Pedro Manuel Baeza Romero & Joaquin Gutierrez Pedrosa
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    bythe Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import base64
import xlrd
from tempfile import NamedTemporaryFile
from openerp.osv import orm, fields
from openerp.tools.translate import _


class MoveImportWizard(orm.TransientModel):
    _name = "move.import.wizard"
    _description = "Picking Import Wizard"

    _columns = {
        'state': fields.selection([('step1', 'Step1'),
                                   ('step2', 'Step2'),
                                   ('done', 'Done')],
                                  'Order State', readonly=True),
        'data': fields.binary('File', required=True),
        'date_picking': fields.date('Date', required=False),
        'wizard_line': fields.one2many('move.import.wizard.line', 'wizard_id',
                                       'Wizard Lines', readonly=True),
    }

    _defaults = {
        'state': 'step1',
        'date_picking': fields.date.context_today,
    }

    def import_excel(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        fileobj = NamedTemporaryFile('w+', suffix='.xls')
        fileobj.write(base64.decodestring(wizard.data))
        book = xlrd.open_workbook(fileobj.name)
        first_sheet = book.sheet_by_index(0)
        line_obj = self.pool['move.import.wizard.line']
        location_obj = self.pool['stock.location']
        product_obj = self.pool['product.product']
        purchase_obj = self.pool['purchase.order']
        sequence = 0
        for row in first_sheet._cell_values:
            if sequence != 0:
                # Buscamos la ubicacion destino por la referencia externa
                location_supplier_id = location_obj.search(
                    cr, uid, [('xls_supplier_location', '=', int(row[2]))])
                destination = location_supplier_id and \
                              location_supplier_id[0] or False
                # Buscamos el producto a traves de la referencia
                product_ids = product_obj.search(
                    cr, uid, [('default_code', '=', row[3])])
                # Buscamos lineas de pedido pendientes con este producto
                if product_ids:
                    order_line_ids = []
                    order_ids = purchase_obj.search(
                        cr, uid, [('shipped', '=', False),
                                  ('state', '=', 'approved'),
                                  ('location_id', '=', destination)])
                    for order in purchase_obj.browse(cr, uid, order_ids,
                                                 context=context):
                        for line in order.order_line:
                            if line.product_id.id == product_ids[0]:
                                order_line_ids.append(line.id)
                        if len(order_line_ids) > 1:
                            order_line_id = False
                        else:
                            order_line_id = order_line_ids[0]
                sequence = sequence + 1
                res = {
                    'date_picking': row[0],
                    'destination': destination,
                    'default_code': row[3],
                    'product_id': product_ids[0],
                    'qty_available': float(row[4]),
                    'order_line_id': order_line_id,
                    'lot_name': row[5],
                    'sequence': sequence,
                    'wizard_id': wizard.id
                }
                line_obj.create(cr, uid, res, context=context)
            else:
                sequence = sequence + 1
        fileobj.close()
        self.write(cr, uid, ids, {'state': 'step2'}, context=context)

        return True

    def create_picking(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        picking_obj = self.pool['stock.picking']
        lot_obj = self.pool['stock.production.lot']
        line_obj = self.pool['move.import.wizard.line']
        purchase_obj = self.pool['purchase.order']
        # Comprobamos que todos los campos estan rellenos
        purchase_order_ids = []
        for line in wizard.wizard_line:
            if not line.product_id:
                raise orm.except_orm(
                    _('Product ERROR!'),
                    _('Not Product for this line, please select one. '
                      'Error line %s.') % line.sequence)
            elif not line.date_picking:
                raise orm.except_orm(
                    _('Date ERROR!'),
                    _('Not Date for this line, please select one. '
                      'Error line %s.') % line.sequence)
            elif not line.destination:
                raise orm.except_orm(
                    _('Destination ERROR!'),
                    _('Not Destination for this line, please select one. '
                      'Error line %s.') % line.sequence)
            elif not line.qty_available:
                raise orm.except_orm(
                    _('Quantity ERROR!'),
                    _('Not Quantity for this line, please select one. '
                      'Error line %s.') % line.sequence)
            elif not line.order_line_id:
                raise orm.except_orm(
                    _('Purchase Line ERROR!'),
                    _('Not Purchase Line for this line, please select one. '
                      'Error line %s.') % line.sequence)
            else:
                purchase_order_ids.append(line.order_line_id.order_id.id)
        purchase_order_ids = set(purchase_order_ids)
        # Buscar pedidos de compra de las lineas
        for purchase_order_id in purchase_order_ids:
            picking_ids = picking_obj.search(
                cr, uid, [('purchase_id', '=', purchase_order_id)])
            for picking in picking_obj.read(cr, uid, picking_ids):
                if picking and picking['state'] in 'draft,assigned':
                    picking_obj.unlink(cr, uid, picking_ids, context=context)
             # Buscar las lineas mismo pedido y ubicacion origen
            line_ids = line_obj.search(
                cr, uid, [('order_id', '=', purchase_order_id),
                          ('wizard_id', '=', wizard.id)])
            purchase = purchase_obj.browse(cr, uid, purchase_order_id,
                                           context=context)
            origin = purchase.partner_id.property_stock_supplier.id
            move_ids = []
            # Cre el lote de ser necesario
            for line in line_obj.browse(cr, uid, line_ids):
                if line.lot_name:
                    res = {
                        'name': line.lot_name,
                        'product_id': line.product_id.id,
                        'date': line.date_picking,
                    }
                lot_id = lot_obj.create(cr, uid, res, context=context)
                # Creo la tupla con los valores de stock.move
                destination = line.destination.id
                res = {
                    'name':
                    line.order_id.name + ': ' + line.product_id.name,
                    'date':
                    line.date_picking,
                    'product_id':
                    line.product_id.id,
                    'product_qty':
                    line.qty_available,
                    'product_uos_qty':
                    line.qty_available,
                    'product_uom':
                    line.product_id.product_tmpl_id.uom_id.id,
                    'prodlot_id':
                    lot_id,
                    'location_id':
                    origin,
                    'location_dest_id':
                    line.destination.id,
                    'address_id':
                    line.order_line_id.order_id.partner_address_id.id,
                    'purchase_line_id':
                    line.order_line_id.id,
                    'note':
                    _('Stock move from Excel import'),
                }
                # Tupla para poder luego asignarla a las lineas del picking
                move_ids.append((0, 0, res))
            # Creo el stock.picking para esas lineas stock.move por pedido
            if move_ids:
                res = {
                    'origin': purchase.name,
                    'type': 'in',
                    'note': _('Stock move from Excel import'),
                    'purchase_id': purchase.id,
                    'location_id': origin,
                    'location_dest_id': destination,
                    'date': wizard.date_picking,
                    'address_id': purchase.partner_address_id.id,
                    'move_lines': move_ids,
                }
                picking_id = picking_obj.create(cr,
                                                uid,
                                                res,
                                                context=context)
                # Confirmo el picking para que realice los movimientos
                picking_obj.draft_validate(cr, uid, [picking_id])
                picking_obj.action_process(cr, uid, [picking_id])
                picking_obj.action_move(cr, uid, [picking_id])
                picking_obj.action_done(cr, uid, [picking_id])
        return {'type': 'ir.actions.act_window_close'}

    def back_step1(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids)[0]
        wizard_line_obj = self.pool['move.import.wizard.line']
        wizard_line_ids = wizard_line_obj.search(
            cr, uid, [('wizard_id', '=', wizard.id)], context=context)
        wizard_line_obj.unlink(cr, uid, wizard_line_ids, context=context)
        self.write(cr, uid, ids, {'state': 'step1'}, context=context)
        return True


class MoveImportWizardLine(orm.TransientModel):
    _name = "move.import.wizard.line"
    _description = "Picking Import Wizard line"
    _order = 'sequence, id'
    _columns = {
        'date_picking': fields.date('Date', required=True),
        'origin': fields.many2one('stock.location', 'Origin'),
        'destination': fields.many2one('stock.location', 'Destination'),
        'default_code': fields.char('Reference', size=64, select=True),
        'qty_available': fields.float('Quantity'),
        'lot_name': fields.char('Serial Number', size=64),
        'product_id': fields.many2one('product.product', 'Product',
                                      domain=[('purchase_ok', '=', True)],
                                      change_default=True),
        'order_line_id': fields.many2one('purchase.order.line',
                                         'Purchase Line',
                                         domain=[('state', '=', 'confirmed')],
                                         change_default=True),
        'order_id': fields.related('order_line_id',
                                   'order_id',
                                   type='many2one',
                                   relation='purchase.order',
                                   string='Purchase Order',
                                   store=True),
        'sequence': fields.integer(
            'Sequence',
            help="Gives the sequence order when displaying a list of lines."),
        'wizard_id': fields.many2one('move.import.wizard', 'Wizard',
                                     required=True, ondelete='cascade',
                                     select=True, readonly=True),
    }


