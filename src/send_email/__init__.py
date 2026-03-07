"""
Send Email Module
Handles email sending through Zavu.dev API
"""
from .zavu_client import send_email_via_zavu, get_zavu_api_key

__all__ = ['send_email_via_zavu', 'get_zavu_api_key']
