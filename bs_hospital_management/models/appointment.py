from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class HospitalAppointment(models.Model):
    _name = 'hospital.appointment'
    _description = 'Hospital Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Appointment Reference',
        readonly=True,
        copy=False,
        tracking=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('hospital.appointment') or 'New'
    )
    patient_id = fields.Many2one('hospital.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hospital.doctor', string='Doctor', required=True, tracking=True)
    appointment_date = fields.Datetime(string='Appointment Date', required=True, tracking=True)
    reason = fields.Text(string='Reason for Visit')
    diagnosis = fields.Text(string='Diagnosis')
    prescription = fields.Text(string='Prescription')
    state = fields.Selection([
        ('draft',     'Draft'),
        ('confirmed', 'Confirmed'),
        ('done',      'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event', copy=False, ondelete='set null')

    _STATUS_MAP = {
        'draft':     'request',
        'confirmed': 'booked',
        'done':      'attended',
        'cancelled': 'cancelled',
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._sync_calendar_event()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('no_hospital_sync') and set(vals) & {'appointment_date', 'patient_id', 'doctor_id', 'state'}:
            for rec in self:
                rec._sync_calendar_event()
        return res

    def unlink(self):
        events = self.mapped('calendar_event_id')
        res = super().unlink()
        events.sudo().unlink()
        return res

    def _sync_calendar_event(self):
        self.ensure_one()
        appointment_type = self.env.ref(
            'hospital_management.hospital_appointment_type', raise_if_not_found=False
        )
        if not appointment_type or not self.appointment_date:
            return

        patient = self.patient_id
        if not patient.partner_id:
            partner = self.env['res.partner'].create({
                'name': patient.name,
                'email': patient.email or False,
                'phone': patient.phone or False,
                'customer_rank': 1,
            })
            patient.partner_id = partner

        stop = self.appointment_date + timedelta(hours=1)
        event_vals = {
            'appointment_type_id': appointment_type.id,
            'appointment_booker_id': patient.partner_id.id,
            'appointment_status': self._STATUS_MAP.get(self.state, 'request'),
            'name': f'{patient.name} - Hospital Appointment',
            'start': self.appointment_date,
            'stop': stop,
            'partner_ids': [(4, patient.partner_id.id)],
        }

        if self.calendar_event_id:
            self.calendar_event_id.with_context(no_mail_to_attendees=True).sudo().write(event_vals)
        else:
            event = self.env['calendar.event'].with_context(no_mail_to_attendees=True).create(event_vals)
            self.with_context(no_hospital_sync=True).sudo().write({'calendar_event_id': event.id})

    def action_view_calendar_event(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'res_id': self.calendar_event_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_confirm(self):
        self.state = 'confirmed'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'