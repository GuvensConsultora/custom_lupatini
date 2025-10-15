
from odoo import models

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance_payment.inv'

    def create_invoices(self):
        orders = self.sale_order_ids
        company = (orders[:1].company_id) or self.env.company
        ou = (orders[:1].operating_unit_id or self.env.user.default_operating_unit_id)

        ctx = dict(self._context or {})
        if ou:
            ctx['default_operating_unit_id'] = ou.id
            journal = self.env['account.journal'].sudo().search([
                ('type', '=', 'sale'),
                ('company_id', '=', company.id),
                ('operating_unit_id', '=', ou.id),
                ('active', '=', True),
            ], limit=1)
            if journal:
                ctx['default_journal_id'] = journal.id
        return super(SaleAdvancePaymentInv, self.with_context(ctx)).create_invoices()
