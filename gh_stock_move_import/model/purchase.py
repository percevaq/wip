# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 Pedro Manuel Baeza Romero & Joaquin Gutierrez Pedrosa
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
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


from openerp.osv import orm


class PurchaseOrderLine(orm.Model):
    _inherit = "purchase.order.line"

    def name_get(self, cr, uid, ids, context=None):
        reads = self.read(
            cr, uid, ids, ['name', 'partner_id', 'order_id'],
            context=context)
        res = []
        for record in reads:
            line = record['name']
            partner_id = record['partner_id'][1]
            order_id = record['order_id'][1]
            name = partner_id + '-' + order_id + '/' + line
            res.append((record['id'], name))
        return res
