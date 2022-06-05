from wangram import PagesBot


class MyBot(PagesBot):
	def addon_handler(self, message):
		if message.text == '📞Order call':
			if self.user.phone is None:
				self.user.update({
					'phone': self.get_contact(message).phone
				})
			self.order_call()

	def order_call(self):
		"""Some code"""


if __name__ == '__main__':
	bot = MyBot(
		'./pages',
		'0000:ASDFGHJKL'
	)
	bot.start(mode='reload_on_error', logging=True)
