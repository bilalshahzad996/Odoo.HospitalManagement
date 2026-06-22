from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _description = "Hospital Patient"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Patient Name", required=True, tracking=True)
    ref = fields.Char(string="Patient Reference", readonly=True, copy=False, tracking=True, default=lambda self: self.env["ir.sequence"].next_by_code("hospital.patient") or "New")
    date_of_birth = fields.Date(string="Date of Birth")
    age = fields.Integer(string="Age", compute="_compute_age", store=True)
    gender = fields.Selection([("male","Male"),("female","Female"),("other","Other")], string="Gender", required=True, tracking=True)
    blood_group = fields.Selection([("A+","A+"),("A-","A-"),("B+","B+"),("B-","B-"),("O+","O+"),("O-","O-"),("AB+","AB+"),("AB-","AB-")], string="Blood Group")
    phone = fields.Char(string="Phone", tracking=True)
    email = fields.Char(string="Email")
    address = fields.Text(string="Address")
    weight = fields.Float(string="Weight (kg)")
    height = fields.Float(string="Height (cm)")
    notes = fields.Text(string="Internal Notes")
    state = fields.Selection([("active","Active"),("discharged","Discharged"),("critical","Critical")], string="Status", default="active", tracking=True)
    appointment_ids = fields.One2many("hospital.appointment", "patient_id", string="Appointments")
    appointment_count = fields.Integer(string="Appointment Count", compute="_compute_appointment_count", store=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact', copy=False, ondelete='set null')


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.partner_id:
                partner = self.env['res.partner'].create({
                    'name': rec.name,
                    'email': rec.email or False,
                    'phone': rec.phone or False,
                    'customer_rank': 1,
                })
                rec.partner_id = partner
        return records

    def write(self, vals):
        res = super().write(vals)
        sync_fields = {'name', 'email', 'phone'}
        if sync_fields & set(vals):
            for rec in self:
                if rec.partner_id:
                    rec.partner_id.write({k: vals[k] for k in sync_fields & set(vals)})
        return res

    @api.depends("date_of_birth")
    def _compute_age(self):
        for rec in self:
            if rec.date_of_birth:
                today = date.today()
                rec.age = today.year - rec.date_of_birth.year - ((today.month, today.day) < (rec.date_of_birth.month, rec.date_of_birth.day))
            else:
                rec.age = 0

    @api.depends("appointment_ids")
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    @api.constrains("date_of_birth")
    def _check_date_of_birth(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > date.today():
                raise ValidationError("Date of Birth cannot be a future date!")

    @api.constrains("weight", "height")
    def _check_weight_height(self):
        for rec in self:
            if rec.weight < 0:
                raise ValidationError("Weight cannot be negative!")
            if rec.height < 0:
                raise ValidationError("Height cannot be negative!")

    def action_view_appointments(self):
        return {"type": "ir.actions.act_window", "name": "Appointments", "res_model": "hospital.appointment", "view_mode": "list,form", "domain": [("patient_id","=",self.id)], "context": {"default_patient_id": self.id}}

    def action_active(self):
        self.state = "active"

    def action_discharged(self):
        self.state = "discharged"

    def action_critical(self):
        self.state = "critical"
