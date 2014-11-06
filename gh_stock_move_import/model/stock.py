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


from openerp.osv import orm, fields


class StockLocation(orm.Model):
    _description = "Location"
    _inherit = "stock.location"

    _columns = {
        'xls_supplier_location': fields.char(
            'XLS Supplier Location',
            size=64,
            required=True,
            help='This field related the location with a logistics supplier'),

    }
    _sql_constraints = [
        ('ref_uniq',
         'unique(supplier_location, company_id)',
         'External Reference must be unique per Company!'),
    ]
