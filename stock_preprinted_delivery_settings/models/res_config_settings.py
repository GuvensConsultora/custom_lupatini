# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
import math

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Cantidad de líneas para albaranes OUT (entregas) - guardado en ir.config_parameter
    preprint_lines_out = fields.Integer(
        string="Líneas por albarán de entregas",
        config_parameter="stock_preprinted_delivery.preprint_lines_out",  # clave del parámetro
        default=25,  # valor por defecto razonable
        help="Cantidad de renglones impresos en remitos/albaranes OUT (entregas).",
    )

    # Cantidad de líneas para albaranes INT (mov. internos) - guardado en ir.config_parameter
    preprint_lines_int = fields.Integer(
        string="Líneas por albarán internos",
        config_parameter="stock_preprinted_delivery.preprint_lines_int",
        default=25,
        help="Cantidad de renglones impresos en remitos/albaranes INT (movimientos internos).",
    )


class AlbaranPrintHelloWizard(models.TransientModel):
    _name = "albaran.print.hello.wizard"
    _description = "Wizard de impresión - Hola"

    message = fields.Char(
        string="Mensaje",
        default="Hola mundo",
        readonly=True
    )
    picking_id = fields.Many2one("stock.picking", string="Albarán", required=True, readonly=True)
    picking_type_code = fields.Selection(related="picking_id.picking_type_code", readonly=True)
    total_lines = fields.Integer(string="Líneas totales", compute="_compute_totals", store=False)
    lines_per_doc = fields.Integer(string="Líneas por documento", required=True)
    expected_docs = fields.Integer(string="Remitos esperados", compute="_compute_totals", store=False)
    detail_note = fields.Html(string="Detalle", sanitize=False, readonly=True)

    @api.depends("picking_id", "lines_per_doc")
    def _compute_totals(self):
        for w in self:
            if not w.picking_id:
                w.total_lines = 0; w.expected_docs = 0; continue
            moves = w.picking_id.move_ids.filtered(
                lambda m: m.state != "cancel" and (m.product_uom_qty or m.quantity_done)
            )
            total = len(moves)
            lpd = max(w.lines_per_doc or 1, 1)
            w.total_lines = total
            w.expected_docs = math.ceil(total / lpd) if total else 0
    
    def action_confirm_preprint(self):
        self.ensure_one()
        return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {"title": "OK", "message": "Confirmado", "type": "success"},
        "context": {"default_picking_id": self.id}, 
        }



    

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_print_intercept(self):
        self.ensure_one()
        if self.picking_type_code not in ("outgoing", "internal"):
            raise UserError("Solo disponible para albaranes OUT o INT.")

        # leer parámetros para líneas por doc
        ICP = self.env["ir.config_parameter"].sudo()
        if self.picking_type_code == "outgoing":
            lpd = int(ICP.get_param("stock_preprinted_delivery.preprint_lines_out", default=25))
        elif self.picking_type_code == "internal":
            lpd = int(ICP.get_param("stock_preprinted_delivery.preprint_lines_int", default=25))
        else:
            lpd = 25

        # crear el wizard con valores iniciales
        wiz = self.env["albaran.print.hello.wizard"].create({
            "picking_id": self.id,
            "lines_per_doc": lpd,
            "message": "Hola mundoooo",
        })

        # abrir ese registro
        view = self.env.ref("stock_preprinted_delivery_settings.view_albaran_print_hello_wizard")
        return {
            "type": "ir.actions.act_window",
            "name": "Imprimir",
            "res_model": "albaran.print.hello.wizard",
            "view_mode": "form",
            "view_id": view.id,
            "res_id": wiz.id,
            "target": "new",
        }


###################################################

        # self.ensure_one()
        # if self.picking_type_code not in ("outgoing", "internal"):
        #     raise UserError("Solo disponible para albaranes OUT o INT.")

        # # Acción completa: res_model + views + view_id + target=new
        # view = self.env.ref("stock_preprinted_delivery_settings.view_albaran_print_hello_wizard")
        # return {
        #     "type": "ir.actions.act_window",
        #     "name": "Imprimir",
        #     "res_model": "albaran.print.hello.wizard",
        #     "view_mode": "form",
        #     "view_id": view.id,
        #     "views": [(view.id, "form")],
        #     "target": "new",
        #     "context": {"default_message": "Hola mundoooo"},

       # }



def _slug(text):                                      # normaliza texto para usar en code/prefix
    text = (text or "").strip().upper()               # mayúsculas y trim
    return "".join(ch for ch in text if ch.isalnum()) # solo A-Z0-9

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    print_sequence_id = fields.Many2one(           # secuencia de impresión (ya creada en el paso anterior)
        "ir.sequence",
        string="Secuencia de impresión",
        help="Secuencia usada para foliar el impreso (no afecta la referencia del albarán).",
        domain="[('company_id','in',[False, company_id])]",
    )

    def _ensure_print_sequence_with_ou(self):      # crea/asigna secuencia con tipo + UO en code
        for ptype in self:                         # iterar tipos seleccionados
            if ptype.print_sequence_id:            # si ya existe, no crear de nuevo
                continue
            ou = ptype.warehouse_id and ptype.warehouse_id.operating_unit_id  # trae UO desde almacén
            if not ou:                             # si no hay UO, no forzar creación
                continue
            type_key = _slug(ptype.code or "ALB")  # clave del tipo (OUT/INT/…)
            ou_key   = _slug(ou.name or ou.code or f"OU{ou.id}")  # clave de la UO
            seq_code = f"print.{type_key}.{ou_key}"               # code interno con tipo y UO
            prefix   = f"{type_key}/{ou_key}/"                    # prefijo visible, ej: OUT/CORDOBA/
            seq = self.env["ir.sequence"].create({                # crear secuencia
                "name": f"Print {ptype.name} - {ou.name}",        # nombre legible
                "implementation": "standard",                     # estándar
                "prefix": prefix,                                 # prefijo con tipo+UO
                "padding": 6,                                     # 000001
                "company_id": ptype.company_id.id or False,       # compañía del tipo
                "code": seq_code,                                 # code interno con tipo+UO
            })
            ptype.print_sequence_id = seq.id                      # asigna al tipo

    @api.model_create_multi
    def create(self, vals_list):                  # (opcional, pero útil) al crear el tipo, asegurar secuencia
        records = super().create(vals_list)       # crea tipos
        records._ensure_print_sequence_with_ou()  # genera secuencia con tipo+UO (si hay UO)
        return records

