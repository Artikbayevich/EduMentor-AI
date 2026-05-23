"""
bot/states.py — FSM state groups for aiogram 3.x.
"""
from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    """HEMIS OAuth2 login flow."""
    waiting_for_hemis   = State()   # User clicked "Login", waiting for callback
    authenticated       = State()   # Access token obtained and stored


class P2PStates(StatesGroup):
    """P2P help request creation flow."""
    choosing_subject    = State()
    entering_description = State()
    setting_coin_offer  = State()
    confirming          = State()
