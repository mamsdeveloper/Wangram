# :TODO
# - test current commit
# - comment all


import json
import os
from typing import Any

from aiogram import Bot, Dispatcher, executor, filters, types
from aiogram.bot.api import TELEGRAM_PRODUCTION

from wangram.types import Page, User


class PagesBot(Bot):
	def __init__(
		self, config: dict[str, str], token, loop=None, connections_limit=None, proxy=None, proxy_auth=None,
		validate_token=None, parse_mode=None, disable_web_page_preview=None, timeout=None, server=TELEGRAM_PRODUCTION
	):
		super().__init__(token, loop, connections_limit, proxy, proxy_auth,
                   validate_token, parse_mode, disable_web_page_preview, timeout, server)

		pages_path = config['pages_path']
		self.pages = {
			page_name: Page.from_folder(os.path.join(pages_path, page_name))
			for page_name in os.listdir(pages_path)
		}
		self.root_page = self.pages[config['root_page']]
		self.curr_page = self.root_page

		if 'users_db_path' in config:
			self.users_db_path = config['users_db_path']
		else:
			self.users_db_path = os.path.join('./users.json')

		self.curr_user = None
		self.dp = Dispatcher(self)
		self.dp.register_message_handler(self._message_handler)
		self.dp.register_callback_query_handler(self._query_handler)

	async def go_home(self):
		page = self.curr_page
		while page.root_page is not None:
			page = page.root_page

		await self.update_page(page)

	async def go_back(self):
		if self.curr_page.root_page is not None:
			await self.update_page(self.curr_page.root_page)

	async def go_forward(self, page_name: str):
		page = self.curr_page.child_pages.get(page_name, None)
		if page is not None:
			await self.update_page(page)

	async def go_path(self, path_name: str):
		path = self.curr_page.pages_pathes.get(path_name, None)
		if path is not None:
			page = self.get_page_by_path(path)
			await self.update_page(page)

	def check_child_page(self, page_name: str) -> str:
		for child_page in self.curr_page.child_pages:
			if child_page.startswith(page_name):
				return child_page

		return None

	def check_page_path(self, path_name: str) -> str:
		for page_path in self.curr_page.pages_pathes:
			if page_path.startswith(path_name):
				return path_name

	def get_page_by_path(self, path: list[str]) -> Page:
		page = self.pages.get(path.pop(0), None)
		while path:
			page = page.child_pages.get(path.pop(0), None)

		return page

	async def update_page(self, page: Page):
		self.curr_page = page

		page_path = [page.name]
		page_ = page.root_page
		while page_ is not None:
			page_path.insert(0, page_.name)
			page_ = page_.root_page

		self.update_userdata(page_path=page_path)
		await self.display_page(page)

	async def display_page(self, page: Page):
		text = page.name if not page.text else page.text
		text = text.format(**self.__dict__)

		if page.inline_btns and page.keyboard_btns:
			markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
			markup.add(*page.keyboard_btns)
			await self.send_message(self.curr_user.id, '🐶', reply_markup=markup)
			markup = types.InlineKeyboardMarkup()
			markup.add(*page.inline_btns)
		elif page.inline_btns:
			markup = types.InlineKeyboardMarkup()
			markup.add(*page.inline_btns)
		elif page.keyboard_btns:
			markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
			markup.add(*page.keyboard_btns)

		text, markup = self.display_addons(text, markup)
		await self.send_message(
			self.curr_user.id,
			text,
			reply_markup=markup
		)

		media_senders = {
			'photo': self.send_photo,
			'video': self.send_video,
			'animation': self.send_animation,
			'audio': self.send_audio,
			'document': self.send_document,
			'media_group': self.send_media_group
		}

		for media in page.media:
			print(media.type, media.data)
			await media_senders[media.type](
				self.curr_user.id,
				media.data
			)

	def display_addons(self, text: str, markup: Any) -> tuple[str, Any]:
		return text, markup

	def init_userdata(self, user: types.User):
		user_id = str(user.id)
		with open(self.users_db_path, 'r') as f:
			users = json.load(f)

		if not user_id in users:
			self.curr_user = User(**user.__dict__, page_path=[self.root_page.name])
			self.update_userdata()
		else:
			self.curr_user = User(**users[user_id])

		self.curr_page = self.get_page_by_path(self.curr_user.page_path)

	def update_userdata(self, values: dict[str, Any] = None, **kwargs):
		values = values if values else {}
		self.curr_user.__dict__.update(**values, **kwargs)
		with open(self.users_db_path, 'r') as f:
			users = json.load(f)
			users.setdefault(str(self.curr_user.id), {}).update(self.curr_user.__dict__)

		with open(self.users_db_path, 'w') as f:
			json.dump(users, f)

	def drop_userdata(self):
		with open(self.users_db_path, 'r') as f:
			users = json.load(f)
			users.pop(str(self.curr_user.id))

		with open(self.users_db_path, 'w') as f:
			json.dump(users, f)

	async def custom_handler(self, message: types.Message):
		await self.send_message(
			self.curr_user.id,
			'Sorry, not such command or page',
		)
		await self.display_page(self.curr_page)

	async def _message_handler(self, message: types.Message):
		self.init_userdata(message.from_user)
		text = message.text

		if (child_page := self.check_child_page(text)) is not None:
			await self.go_forward(child_page)
		elif (page_path := self.check_page_path(text)) is not None:
			await self.go_path(page_path)
		elif text == self.curr_page.nav_back:
			await self.go_back()
		elif text == self.curr_page.nav_root:
			await self.go_home()
		else:
			await self.custom_handler(message)

	async def custom_query_handler(self, call: types.CallbackQuery):
		await self.send_message(
			self.curr_user.id,
			'Sorry, not such command or page',
		)
		await self.display_page(self.curr_page)

	async def _query_handler(self, call: types.CallbackQuery):
		self.init_userdata(call.from_user)
		data = call.data

		if (child_page := self.check_child_page(data)) is not None:
			await self.go_forward(child_page)
		elif (page_path := self.check_page_path(data)) is not None:
			await self.go_path(page_path)
		elif data == self.curr_page.nav_back:
			await self.go_back()
		elif data == self.curr_page.nav_root:
			await self.go_home()
		else:
			await self.custom_handler(call)


if __name__ == '__main__':
	bot = PagesBot({'pages_path': './examples/example_1/pages', 'root_page': 'Menu'},
	               '5155114149:AAEoOZL9Q9VZrFLYMW6qva_rrxYg-2J_njs')
	
	executor.start_polling(bot.dp, skip_updates=True)
