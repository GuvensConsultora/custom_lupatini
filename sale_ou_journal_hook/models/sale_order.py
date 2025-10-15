
from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        """Inyecta OU y diario de ventas por OU cuando se prepara la factura"""
        self.ensure_one()
        vals = super()._prepare_invoice()

        ou = self.operating_unit_id or self.env.user.default_operating_unit_id
        if ou and not vals.get('operating_unit_id'):
            vals['operating_unit_id'] = ou.id

        if ou and not vals.get('journal_id'):
            company = self.company_id or self.env.company
            journal = self.env['account.journal'].sudo().search([
                ('type', '=', 'sale'),
                ('company_id', '=', company.id),
                ('operating_unit_id', '=', ou.id),
                ('active', '=', True),
            ], limit=1)
            if journal:
                vals['journal_id'] = journal.id
        return vals
