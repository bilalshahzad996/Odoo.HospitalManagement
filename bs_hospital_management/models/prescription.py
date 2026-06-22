from odoo import models, fields, api

class HospitalPrescription(models.Model):
    _name = "hospital.prescription"
    _description = "Hospital Prescription"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Prescription Reference", readonly=True, copy=False, tracking=True, default=lambda self: self.env["ir.sequence"].next_by_code("hospital.prescription") or "New")
    patient_id = fields.Many2one("hospital.patient", string="Patient", required=True, tracking=True)
    doctor_id = fields.Many2one("hospital.doctor", string="Doctor", required=True, tracking=True)
    appointment_id = fields.Many2one("hospital.appointment", string="Appointment")
    date = fields.Date(string="Prescription Date", default=fields.Date.today, required=True)
    notes = fields.Text(string="Doctor Notes")
    state = fields.Selection([("draft","Draft"),("confirmed","Confirmed"),("uploaded","Uploaded to Portal")], string="Status", default="draft", tracking=True)
    prescription_line_ids = fields.One2many("hospital.prescription.line", "prescription_id", string="Medicines")
    pdf_file = fields.Binary(string="Uploaded PDF", attachment=True)
    pdf_filename = fields.Char(string="PDF Filename")

    def action_confirm(self):
        self.state = "confirmed"

    def action_upload_portal(self):
        self.state = "uploaded"

    def action_draft(self):
        self.state = "draft"

    def action_print_prescription(self):
        return self.env.ref("hospital_management.action_report_prescription").report_action(self)


class HospitalPrescriptionLine(models.Model):
    _name = "hospital.prescription.line"
    _description = "Prescription Line"

    prescription_id = fields.Many2one("hospital.prescription", string="Prescription")
    medicine_name = fields.Char(string="Medicine", required=True)
    dosage = fields.Char(string="Dosage")
    frequency = fields.Char(string="Frequency")
    duration = fields.Char(string="Duration")
    notes = fields.Char(string="Notes")
