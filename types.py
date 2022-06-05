import json
import os
from typing import Any

from telebot.types import (InlineKeyboardButton, InputMediaAudio,
                           InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, KeyboardButton)


class Page:
	def __init__(self, folder_path: str, name: str, text: str, config: dict[str, Any]) -> None:
		self.folder_path = folder_path
		self.name = name
		self.text = text
		self.root_page = None

		self.child_pages = {}
		# if folder path setted (so supposedly page created by from_folder)
		# recursive add child pages by from_page method
		if folder_path is not None:
			for child_page in os.listdir(self.folder_path):
				child_path = os.path.join(self.folder_path, child_page)
				if os.path.isdir(child_path):
					self.child_pages[child_page] = Page.from_folder(child_path)
					self.child_pages[child_page].root_page = self

		self.nav_root = ''
		self.nav_back = ''
		self.pages_pathes = {}
		self.keyboard_btns = []
		self.update_keyboard_btns(config.get('keyboard_btns', {}))
		self.inline_btns = []
		self.update_inline_btns(config.get('inline_btns', {}))
		self.media = []
		self.update_media(config.get('media', []))

	def __repr__(self) -> str:
		return (f'Page(name="{self.name}", text="{self.text[:10]}...")')

	def __getitem__(self, key):
		return self.child_pages[key]

	def update_keyboard_btns(self, btns: dict[str, str]):
		"""Update page keyboard buttons with telebot KeyboardButtons relative to it`s types.
		Supported keyboard buttons types:
			$nav_root: button to return home page
			$nav_back: button to return previous page
			$path: button to go to specific page 
			$child_pages: many buttons to go to child pages of current page
			$custom: buttons for custom user action

		Args:
			btns (dict[str, str]): buttons` texts and types
		"""

		for btn_text, btn_type in btns.items():
			if '$nav_root' in btn_type:
				self.nav_root = btn_text
				self.keyboard_btns.append(KeyboardButton(btn_text))
			elif '$nav_back' in btn_type:
				self.nav_back = btn_text
				self.keyboard_btns.append(KeyboardButton(btn_text))
			elif '$path' in btn_type:
				path = btn_type.split(':')[1].split('.')
				self.pages_pathes[btn_text] = path
				self.keyboard_btns.append(KeyboardButton(btn_text))
			elif '$child_pages' in btn_type:
				self.keyboard_btns += [
					KeyboardButton(child_page)
					for child_page in self.child_pages
				]
			elif '$custom' in btn_type:
				self.keyboard_btns.append(KeyboardButton(btn_text))
			else:
				print(f'Unknown button type "{btn_type}" at "{self.name}" page')

	def update_inline_btns(self, btns: dict[str, list[Any]]):
		"""Update page inline buttons with telebot InlineKeyboardButton relative to it`s types.
		Supported inline buttons types:
			$nav_root: button to return home page
			$nav_back: button to return previous page
			$path: button to go to specific page. Args: [path: list[str]]
			$child_pages: many buttons to go to child pages of current page
			$url: link button. Args: [link: str]
			$login: authorization user on website. Args: [url: str] 
			$custom: buttons for custom user action. Args: [callback_data: str]

		Args:
			btns (dict[str, list[Any]]): buttons texts and arguments. First item in arguments must be button type
		"""

		for btn_text, btn_args in btns.items():
			if not len(btn_args):
				print(f'Button "{btn_text}" has not type at "{self.name}" page')

			if '$nav_root' in btn_args[0]:
				self.nav_root = btn_text
				self.keyboard_btns.append(InlineKeyboardButton(btn_text))
			elif '$nav_back' in btn_args[0]:
				self.nav_back = btn_text
				self.keyboard_btns.append(InlineKeyboardButton(btn_text))
			elif '$path' in btn_args[0]:
				path = btn_args[1]
				self.btns_pathes[btn_text] = path
				self.keyboard_btns.append(KeyboardButton(btn_text))
			elif '$child_pages' in btn_args[0]:
				self.inline_btns += [
					InlineKeyboardButton(child_page, callback_data=child_page)
					for child_page in self.child_pages
				]
			elif '$url' in btn_args[0]:
				self.inline_btns.append(
					InlineKeyboardButton(btn_text, url=btn_args[1]))
			elif '$login' in btn_args[0]:
				self.inline_btns.append(
					InlineKeyboardButton(btn_text, login_url=btn_args[1]))
			elif '$custom' in btn_args[0]:
				self.inline_btns.append(
					InlineKeyboardButton(btn_text, callback_data=(btn_args[1] if len(btn_args) > 1 else btn_text)))
			elif '$pay' in btn_args[0]:
				pass  # Not implemented
			else:
				print(f'Unknown button type "{btn_args[0]}" at "{self.name}" page')

	def update_media(self, media: list[list[str, Any]]):
		media_types = {
			'img': InputMediaPhoto,
			'video': InputMediaVideo,
			'audio': InputMediaAudio,
			'doc': InputMediaDocument
		}
		for media_type, media_data in media:
			if media_type == 'media_group':
				group = []
				for media_type, media_data in media_data:
					group.append(media_types[media_type](media_data))
				self.media.append(group)
			else:
				self.media.append(media_types[media_type](media_data))

	def rec_print(self, counter=0):
		print('    ' * counter + str(self))
		for child_page in self.child_pages.values():
			child_page.rec_print(counter + 1)

	@classmethod
	def from_folder(cls, folder_path: str) -> 'Page':
		name = os.path.split(folder_path)[1]
		config_path = os.path.join(folder_path, 'config.json')
		with open(config_path, 'r') as f:
			config = json.load(f)

		text_path = os.path.join(folder_path, 'test.txt')
		if os.path.exists(text_path):
			with open(text_path, 'r') as f:
				text = f.read()
		else:
			text = ''

		return cls(folder_path, name, text, config)


class User():
	def __init__(
		self, id: int, page_path: list[str], first_name: str, last_name: str = None,
		username: str = None, phone: str = None, **kwargs
	) -> None:
		self.id = id
		self.page_path = page_path
		self.first_name = first_name
		self.last_name = last_name
		self.username = username
		self.phone = phone

	def __repr__(self) -> str:
		return f'User(id="{self.id}", first_name="{self.first_name}", username="{self.username}")'


if __name__ == '__main__':
	page = Page.from_folder('./examples/example_1/pages/Menu')
	print('Parsed pages:\n')
	page.rec_print()

	print('\nFirst page media:\n')
	print(*page.media, sep='\n')

	print('\nFirst page btns:\n')
	print(*page.keyboard_btns, sep='\n')
	print(*page.inline_btns, sep='\n')

	print(page.media)
	# user = User(10, ['10', '20'], 'alex', 'aaa', '@somename', phone='10000001')
