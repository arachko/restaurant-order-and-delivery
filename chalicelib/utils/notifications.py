from typing import List

from chalicelib.utils.boto_clients import ses_client
from chalicelib.utils.logger import logger


def send_email_ses(emails_to: List, email_from: str, subject: str, message: str):
    logger.info(f'Sending message to emails {emails_to=}, {subject=}')
    charset = "UTF-8"
    response = ses_client.send_email(
        Destination={"ToAddresses": emails_to},
        Message={
            "Body": {"Text": {"Charset": charset, "Data": message}},
            "Subject": {"Charset": charset, "Data": subject},
        },
        Source=email_from,
    )
    logger.info(f'Message has been sent, message_id={response.get("MessageId")}')

