# handlers/private/boosting.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from typing import Callable, Optional

from database.models import User, Channel, Order
from services.channel_service import ChannelService
from services.order_service import OrderService
from utils.keyboards import get_boosting_menu_kb, get_boost_type_kb, get_channel_selection_kb, get_order_confirmation_kb, get_main_menu_kb, get_channel_manage_kb
from utils.callbacks import MainMenuCallback, BoostOrderCallback, ChannelCallback
from utils.states import Form

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "new_boost"))
async def new_boost_start(call: CallbackQuery, state: FSMContext, _: Callable[[str], str]):
    await call.message.edit_text(_("boosting_menu.choose_type"), reply_markup=get_boost_type_kb(_))
    await state.set_state(Form.boosting_choose_type)
    await call.answer()

@router.callback_query(BoostOrderCallback.filter(F.action == "type_select"), Form.boosting_choose_type)
async def new_boost_choose_type(call: CallbackQuery, callback_data: BoostOrderCallback, state: FSMContext, user: User, _: Callable[[str], str]):
    order_type = callback_data.order_type
    await state.update_data(order_type=order_type)

    channels = user.channels
    if not channels:
        await call.message.edit_text(_("initial_channel_setup.no_channels_added"), reply_markup=get_boosting_menu_kb(_)) # User error: no channels
        await state.clear()
        await call.answer(_("initial_channel_setup.no_channels_added"), show_alert=True)
        return

    await call.message.edit_text(_("boosting_menu.channel_choose"), reply_markup=get_channel_selection_kb(channels, _))
    await state.set_state(Form.boosting_choose_channel)
    await call.answer()

@router.callback_query(ChannelCallback.filter(F.action == "select"), Form.boosting_choose_channel)
async def new_boost_choose_channel(call: CallbackQuery, callback_data: ChannelCallback, state: FSMContext, user: User, _: Callable[[str], str]):
    channel_id = callback_data.channel_id
    selected_channel = next((c for c in user.channels if c.id == channel_id), None)
    if not selected_channel:
        await call.message.edit_text(_("error.default"), reply_markup=get_boosting_menu_kb(_))
        await state.clear()
        await call.answer(_("error.default"), show_alert=True)
        return

    await state.update_data(channel_id=channel_id, channel_title=selected_channel.title)
    await call.message.edit_text(_("boosting_menu.enter_subscribers"))
    await state.set_state(Form.boosting_enter_subscribers)
    await call.answer()

@router.message(Form.boosting_enter_subscribers, F.text)
async def new_boost_enter_subscribers(message: Message, state: FSMContext, user: User, _: Callable[[str], str]):
    try:
        requested_subscribers = int(message.text)
        if requested_subscribers < 100:
            await message.answer(_("boosting_menu.invalid_sub_amount"))
            return
    except ValueError:
        await message.answer(_("boosting_menu.invalid_sub_amount"))
        return

    data = await state.get_data()
    order_type = data["order_type"]
    channel_title = data["channel_title"]
    
    cost_per_sub = 1
    if order_type == "turbo":
        cost_per_sub = 2
    total_cost = requested_subscribers * cost_per_sub

    if user.balance < total_cost:
        await message.answer(_("error.not_enough_credits").format(balance=user.balance, cost=total_cost), reply_markup=get_boosting_menu_kb(_))
        await state.clear()
        return

    confirmation_text = _("boosting_menu.confirm_order").format(
        channel_title=channel_title,
        order_type=_("boosting_menu.normal_type" if order_type == "normal" else "boosting_menu.turbo_type"),
        subscribers=requested_subscribers,
        cost=total_cost
    )
    await state.update_data(requested_subscribers=requested_subscribers, total_cost=total_cost)
    await message.answer(confirmation_text, reply_markup=get_order_confirmation_kb(_))
    await state.set_state(Form.boosting_confirm_order)

@router.callback_query(BoostOrderCallback.filter(F.action == "confirm"), Form.boosting_confirm_order)
async def new_boost_confirm_order(call: CallbackQuery, state: FSMContext, user: User, order_service: OrderService, _: Callable[[str], str]):
    data = await state.get_data()
    order_type = data["order_type"]
    requested_subscribers = data["requested_subscribers"]
    channel_id = data["channel_id"]

    selected_channel = next((c for c in user.channels if c.id == channel_id), None)
    if not selected_channel:
        await call.message.edit_text(_("error.default"), reply_markup=get_main_menu_kb(_))
        await state.clear()
        await call.answer(_("error.default"), show_alert=True)
        return

    order = await order_service.create_boost_order(user, selected_channel, order_type, requested_subscribers)
    if order:
        await call.message.edit_text(_("boosting_menu.order_launched").format(order_id=order.id), reply_markup=get_main_menu_kb(_))
        await state.clear()
    else:
        await call.message.edit_text(_("error.default"), reply_markup=get_main_menu_kb(_))
    
    await call.answer()

@router.callback_query(BoostOrderCallback.filter(F.action == "cancel"), Form.boosting_confirm_order)
async def new_boost_cancel_order(call: CallbackQuery, state: FSMContext, _: Callable[[str], str]):
    await call.message.edit_text(_("common.cancel"), reply_markup=get_main_menu_kb(_))
    await state.clear()
    await call.answer(_("common.cancel"))

@router.callback_query(MainMenuCallback.filter(F.action == "active_boosts"))
async def show_active_boosts(call: CallbackQuery, user: User, order_service: OrderService, _: Callable[[str], str]):
    active_orders = await order_service.get_active_orders(user.id)
    if not active_orders:
        await call.message.answer(_("boosting_menu.no_active_boosts")) # Need to add this key
    else:
        # Format and display active orders
        # Example table format: Название чата | @username | Заказано | Выполнено | Ошибки | ETA | .log
        response_text = "<b>" + _("boosting_menu.active_orders") + "</b>\n\n"
        for order in active_orders:
            channel = next((c for c in user.channels if c.id == order.channel_id), None)
            channel_name = channel.title if channel else f"ID: {order.channel_id}"
            
            response_text += (
                f"<b>{channel_name}</b> (@{channel.username if channel else 'N/A'})\n"
                f"Заказано: {order.requested_subscribers} | Выполнено: {order.fulfilled_subscribers} "
                f"| Ошибки: {order.errors}\n"
                f"ETA: {order.eta.strftime('%Y-%m-%d %H:%M') if order.eta else 'N/A'} | Статус: {order.status}\n\n"
            )
        await call.message.answer(response_text, parse_mode='HTML', reply_markup=get_boosting_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "boost_history"))
async def show_boost_history(call: CallbackQuery, user: User, order_service: OrderService, _: Callable[[str], str]):
    completed_orders = await order_service.get_order_history(user.id)
    if not completed_orders:
        await call.message.answer(_("boosting_menu.no_boost_history")) # Need to add this key
    else:
        response_text = "<b>" + _("boosting_menu.order_history") + "</b>\n\n"
        for order in completed_orders:
            channel = next((c for c in user.channels if c.id == order.channel_id), None)
            channel_name = channel.title if channel else f"ID: {order.channel_id}"
            
            response_text += (
                f"<b>{channel_name}</b> ({order.order_type.capitalize()})\n"
                f"Заказано: {order.requested_subscribers} | Выполнено: {order.fulfilled_subscribers}\n"
                f"Стоимость: {order.cost_credits} кредитов | Завершено: {order.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        await call.message.answer(response_text, parse_mode='HTML', reply_markup=get_boosting_menu_kb(_))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "my_channels"))
async def show_my_channels(call: CallbackQuery, user: User, _: Callable[[str], str]):
    channels = user.channels
    if not channels:
        await call.message.edit_text(_("initial_channel_setup.no_channels_added"), reply_markup=get_boosting_menu_kb(_))
        await call.answer(_("initial_channel_setup.no_channels_added"), show_alert=True)
        return

    # List channels and offer to manage them individually
    response_text = _("boosting_menu.my_channels_list").format(max_channels=user.max_channels_slots) # Need this key
    builder = InlineKeyboardBuilder()
    for channel in channels:
        builder.row(InlineKeyboardButton(
            text=f"{channel.title} (@{channel.username})" if channel.username else channel.title,
            callback_data=ChannelCallback(action="manage", channel_id=channel.id).pack()
        ))
    
    # Option to buy more slots
    builder.row(InlineKeyboardButton(text=_("my_channels.buy_more_slots"), callback_data=MainMenuCallback(action="buy_channel_slots").pack())) # Need key
    builder.row(InlineKeyboardButton(text=_("common.back"), callback_data=MainMenuCallback(action="boosting").pack()))
    
    await call.message.edit_text(response_text, reply_markup=builder.as_markup())
    await call.answer()

@router.callback_query(ChannelCallback.filter(F.action == "manage"))
async def manage_single_channel(call: CallbackQuery, callback_data: ChannelCallback, user: User, channel_service: ChannelService, _: Callable[[str], str]):
    channel_id = callback_data.channel_id
    selected_channel = next((c for c in user.channels if c.id == channel_id), None)
    if not selected_channel:
        await call.message.edit_text(_("error.default"), reply_markup=get_main_menu_kb(_))
        await call.answer(_("error.default"), show_alert=True)
        return
    
    # Placeholder for channel management options
    # "Статистика" (анализ по активности, подписке, отписке, охвату)
    # "Чаты для сбора активных" — можно выбрать чаты-доноры
    stats = await channel_service.get_channel_statistics(selected_channel)
    current_subs = stats.get("subscribers_count", "N/A")
    channel_info_text = (
        f"<b>{selected_channel.title}</b> (@{selected_channel.username or 'N/A'})\n"
        f"Текущие подписчики: {current_subs}\n"
        f"Статистика:\n"
        f"  Рост: {stats.get('daily_growth_avg', 'N/A')}\n"
        f"  Охват: {stats.get('views_per_post_avg', 'N/A')}\n"
        # Add more statistics here
    )
    await call.message.edit_text(channel_info_text, parse_mode='HTML', reply_markup=get_channel_manage_kb(selected_channel, _))
    await call.answer()

@router.callback_query(MainMenuCallback.filter(F.action == "buy_channel_slots"))
async def buy_channel_slots(call: CallbackQuery, user: User, _: Callable[[str], str]):
    # Dynamic pricing for slots
    # This is a dummy for now. Real implementation would show prices and confirm purchase.
    current_slots = user.max_channels_slots
    next_slot_price = {1: 500, 2: 1000, 3: 2000, 4: 4000, 5: 8000}.get(current_slots + 1, 16000) # Example dynamic pricing
    
    if user.balance < next_slot_price:
        await call.message.answer(_("error.not_enough_credits").format(balance=user.balance, cost=next_slot_price), show_alert=True)
        await call.answer()
        return

    # Dummy logic to buy a slot
    # await user_service.deduct_user_balance(user, next_slot_price)
    # await user_service.update_user_channel_slots(user.id, current_slots + 1)
    # user.max_channels_slots += 1 # Update in-memory
    await call.message.answer(_("my_channels.buy_slot_success").format(new_slots=current_slots + 1), reply_markup=get_boosting_menu_kb(_)) # Need key
    await call.answer(_("my_channels.buy_slot_success_alert"), show_alert=True)
