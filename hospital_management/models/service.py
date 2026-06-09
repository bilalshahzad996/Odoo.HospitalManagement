from odoo import models, fields

class HospitalService(models.Model):
    _name = "hospital.service"
    _description = "Hospital Service"
    _rec_name = "name"

    name = fields.Char(string="Service Name", required=True)
    service_type = fields.Selection([
        ("consultation",  "Consultation"),
        ("lab_test",      "Lab Test"),
        ("xray",          "X-Ray / Imaging"),
        ("surgery",       "Surgery"),
        ("physiotherapy", "Physiotherapy"),
        ("nursing",       "Nursing Care"),
        ("room",          "Room / Bed Charges"),
        ("medicine",      "Medicine"),
        ("ambulance",     "Ambulance"),
        ("other",         "Other"),
    ], string="Service Type", required=True)
    price = fields.Float(string="Default Price", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)