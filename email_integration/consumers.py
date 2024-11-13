import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer


class EmailImportProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.group_name = "email_import_progress"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        except Exception as e:
            logging.error(f"Error occurred during connection: {str(e)}")
            raise

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception as e:
            logging.error(f"Error occurred during disconnection: {str(e)}")
            raise

    async def update_message_progress(self, event):
        try:
            if "checked_messages" in event:
                await self.send(text_data=json.dumps({
                    "checked_messages": event["checked_messages"]
                }))
            elif "progress" in event and "message" in event:
                await self.send(text_data=json.dumps({
                    "progress": event["progress"],
                    "message": event["message"]
                }))
            else:
                logging.warning("Invalid event data")

        except Exception as e:
            logging.error(f"Error occurred during progress update: {str(e)}")
            raise
