def get_new_order_notification_message(order_record):
    return f"""
        Order details: \n
        ID: {order_record.get('id_')}\n
        Items: {order_record.get('menu_items')}\n
        Amount: {order_record.get('amount')}\n
        Address: {order_record.get('delivery_address')}\n
        Phone: {order_record.get('user_phone_number')}\n
        User ID: {order_record.get('user_id')}\n
        Comment: {order_record.get('comment_')}
    """
