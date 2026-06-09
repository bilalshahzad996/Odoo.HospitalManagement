from odoo import models, fields


class HospitalDoctor(models.Model):
    _name = 'hospital.doctor'
    _description = 'Hospital Doctor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Doctor Name', required=True, tracking=True)
    specialization = fields.Selection([
        ('general',     'General Physician'),
        ('cardiology',  'Cardiology'),
        ('neurology',   'Neurology'),
        ('orthopedics', 'Orthopedics'),
        ('pediatrics',  'Pediatrics'),
        ('dermatology', 'Dermatology'),
        ('other',       'Other'),
    ], string='Specialization', required=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    degree = fields.Char(string='Degree')
    experience_years = fields.Integer(string='Years of Experience')
    appointment_ids = fields.One2many('hospital.appointment', 'doctor_id', string='Appointments')
