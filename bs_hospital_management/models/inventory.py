from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HospitalInventory(models.Model):
    _name = "hospital.inventory"
    _description = "Hospital Medical Inventory"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "product_id"

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        tracking=True,
        domain="[('type','in',['product','consu'])]"
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        related="product_id.product_tmpl_id",
        store=True
    )
    category = fields.Selection([
        ("medicine",   "Medicine"),
        ("equipment",  "Equipment"),
        ("consumable", "Consumable"),
        ("surgical",   "Surgical"),
        ("diagnostic", "Diagnostic"),
        ("other",      "Other"),
    ], string="Category", required=True, tracking=True)
    supplier = fields.Char(string="Supplier")
    description = fields.Text(string="Description")
    location_id = fields.Many2one(
        "stock.location",
        string="Storage Location",
        domain="[('usage','=','internal')]"
    )

    # ── Read quantity directly from Odoo stock ────────────────
    quantity_on_hand = fields.Float(
        string="Quantity on Hand",
        related="product_id.qty_available",
        readonly=True
    )

    def action_view_product(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Product",
            "res_model": "product.template",
            "res_id": self.product_tmpl_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_stock(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Stock Moves",
            "res_model": "stock.move",
            "view_mode": "list,form",
            "domain": [("product_id", "=", self.product_id.id)],
        }

    def action_open_inventory_adjustment(self):
        """Open Odoo native inventory adjustment"""
        return {
            "type": "ir.actions.act_window",
            "name": "Inventory Adjustment",
            "res_model": "stock.quant",
            "view_mode": "list",
            "domain": [("product_id", "=", self.product_id.id)],
            "context": {
                "default_product_id": self.product_id.id,
                "default_location_id": self.location_id.id if self.location_id else False,
                "search_default_product_id": self.product_id.id,
            }
        }