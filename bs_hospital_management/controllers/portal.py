from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class HospitalPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'prescription_count' in counters:
            values['prescription_count'] = request.env['hospital.prescription'].search_count([
                ('patient_id.email', '=', request.env.user.email),
                ('state', '=', 'uploaded')
            ])
        return values

    @http.route(['/my/prescriptions'], type='http', auth='user', website=True)
    def portal_prescriptions(self, **kwargs):
        prescriptions = request.env['hospital.prescription'].sudo().search([
            ('patient_id.email', '=', request.env.user.email),
            ('state', '=', 'uploaded')
        ])
        return request.render('hospital_management.portal_prescriptions', {
            'prescriptions': prescriptions,
        })

    @http.route(['/my/prescriptions/<int:prescription_id>'], type='http', auth='user', website=True)
    def portal_prescription_detail(self, prescription_id, **kwargs):
        prescription = request.env['hospital.prescription'].sudo().browse(prescription_id)
        return request.render('hospital_management.portal_prescription_detail', {
            'prescription': prescription,
        })