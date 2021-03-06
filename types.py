import json
import os
import re
from io import BufferedReader
from typing import Any, Union

from aiogram.types import (InputMediaAnimation, InputMediaAudio,
                           InputMediaDocument, InputMediaPhoto,
                           InputMediaVideo, KeyboardButton, InlineKeyboardButton)


URL_PATTERN = r'^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)'


class Media():
	media_types = {
		'photo': InputMediaPhoto,
		'video': InputMediaVideo,
		'animation': InputMediaAnimation,
		'audio': InputMediaAudio,
		'document': InputMediaDocument
	}

	def __init__(self, type: str, data: Union[str, list[list[str, str]]]) -> None:
		self.type = type
		if self.type == 'media_group':
			self._data = [Media(*m) for m in data]
		else:
			self._data = data

	def __repr__(self) -> str:
		return f'Media(type="{self.type}", data={self._data})'

	@property
	def data(self) -> Union[str, BufferedReader, list[BufferedReader]]:
		if self.type == 'media_group':
			return [self.media_types[m.type](media=m.data) for m in self._data]
		if re.match(URL_PATTERN, self._data) is not None:
			return self._data
		else:
			return open(self._data, 'rb')


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
		return f'Page(name="{self.name}", text="{self.text[:10]}...", child_pages={list(self.child_pages.keys())})'

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
			elif '$custom' in btn_args[0]:
				self.inline_btns.append(
					InlineKeyboardButton(btn_text, callback_data=(btn_args[1] if len(btn_args) > 1 else btn_text)))
			elif '$pay' in btn_args[0]:
				pass  # Not implemented
			elif '$login' in btn_args[0]:
				pass  # Not implemented
			else:
				print(f'Unknown button type "{btn_args[0]}" at "{self.name}" page')

	def update_media(self, media: list[Media]):
		for media_type, media_data in media:
			self.media.append(Media(media_type, media_data))

	def rec_print(self, counter=0):
		print('    ' * counter + str(self))
		for child_page in self.child_pages.values():
			child_page.rec_print(counter + 1)

	@classmethod
	def from_folder(cls, folder_path: str) -> 'Page':
		name = os.path.split(folder_path)[1]
		config_path = os.path.join(folder_path, 'config.json')
		with open(config_path, 'rb') as f:
			config = json.load(f)

		text_path = os.path.join(folder_path, 'text.txt')
		if os.path.exists(text_path):
			with open(text_path, 'r', encoding='utf-8') as f:
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
	page = Page.from_folder('./examples/example_1/pages/Secret Page')
	print('Parsed pages:\n')
	page.rec_print()

	print('\nFirst page media:\n')
	print(*page.media, sep='\n')

	print('\nFirst page btns:\n')
	print(*page.keyboard_btns, sep='\n')
	print(*page.inline_btns, sep='\n')

	print(page.media)
	# user = User(10, ['10', '20'], 'alex', 'aaa', '@somename', phone='10000001')
