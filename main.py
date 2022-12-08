import datetime
import pytz
from kivy import Config
from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore
from kivy.uix.label import Label
from kivy.graphics import Rectangle
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.properties import Clock
from random import randint
import sqlite3
import os
import csv

from kivy.utils import get_color_from_hex

if dp(105) * 3 > 0:
	Window.minimum_width = Window.minimum_height = dp(105) * 3


class AppManager(ScreenManager):
	""" The ScreenManager of the app that controls the screens"""
	
	Background_Music = SoundLoader.load("troll.ogg")
	
	def __init__(self, **kwargs):
		super(AppManager, self).__init__(**kwargs)
		
		if self.Background_Music:
			self.Background_Music.loop = True
			self.Background_Music.volume = 0.0
			self.Background_Music.play()
		
		persistent_save_file = App.get_running_app().user_data_dir
		self.db_connection = sqlite3.connect(os.path.join(persistent_save_file, 'stb.sqlite3'),
											 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
		self.db_connection.execute("CREATE TABLE IF NOT EXISTS games (date_time TIMESTAMP PRIMARY KEY, score INTEGER)")
	
	def switch_music_on_off(self):
		if self.Background_Music.volume != 0:
			self.Background_Music.volume = 0
		else:
			self.Background_Music.volume = 0.5


class MenuScreen(Screen):
	""" The screen that represents the Menu"""
	
	def __init__(self, **kwargs):
		super(MenuScreen, self).__init__(**kwargs)
		self.bg_ball = Image(allow_stretch=True, keep_ratio=False,
							 size_hint=(None, None),
							 size=(dp(105), dp(105)))
		self.add_widget(self.bg_ball)
		self.vx = dp(3)
		self.vy = dp(3)
		
		Clock.schedule_interval(self.update_ball, 1 / 60)
	
	def on_size(self, _widget, _value):
		""" Centers the ball when resizing the screen."""
		self.bg_ball.pos = self.width / 2 - self.bg_ball.width / 2, self.height / 2 - self.bg_ball.height / 2
	
	def update_ball(self, _delta):
		""" Make a DVD-like ball bouncing screen."""
		self.bg_ball.pos = self.bg_ball.x + self.vx, self.bg_ball.y + self.vy
		
		if self.bg_ball.x <= 0 or self.bg_ball.x >= self.width - self.bg_ball.width:
			self.vx *= -1
		
		if self.bg_ball.y <= 0 or self.bg_ball.y >= self.height - self.bg_ball.height:
			self.vy *= -1


class MenuButton(Button):
	""" Button wrapped class for the buttons in the menu screen"""
	
	def on_touch_move(self, touch):
		if not ((self.x <= touch.x <= self.x + self.width) and (self.y <= touch.y <= self.y + self.height)):
			self.background_color = 1, 1, 1
			self.color = 0, 0, 0


class StatsScreen(Screen):
	"""
	The screen responsible for displaying the highscore and other important stats.
	"""
	Highscore = NumericProperty(0)
	GamesPlayed = NumericProperty(0)
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		Clock.schedule_once(self.update_stats_screen, 0)
	
	def update_highscore(self, score: int):
		""" Updates the highscore and saves it to the .txt file"""
		if score > self.Highscore:
			self.Highscore = score
			
	def update_stats_screen(self, _dt):
		self.get_highscore()
		self.update_games_played()
	
	def get_highscore(self):
		conn = self.manager.db_connection
		for score in conn.execute("SELECT score FROM games"):
			if score[0] > self.Highscore:
				self.Highscore = score[0]
	
	def update_db(self, score: tuple[datetime, int]):
		print("Updating Database...")
		conn = self.manager.db_connection
		conn.execute("INSERT INTO games VALUES(?, ?)", (score[0], score[1]))
		conn.commit()
		print("Update Committed!")
		
	def update_games_played(self):
		conn = self.manager.db_connection
		
		games_count = None
		for row in conn.execute("SELECT COUNT(score) from games"):
			games_count = row[0]
		
		self.GamesPlayed = games_count
		
	def update_list(self):
		
		past_games_grid = self.ids.past_games
		for label in past_games_grid.children[::-1]:
			past_games_grid.remove_widget(label)
		
		conn = self.manager.db_connection
		for row in conn.execute("SELECT * FROM games ORDER BY date_time DESC"):
			date, score = row
			local_tz = datetime.datetime.now().astimezone().tzinfo
			date = pytz.utc.localize(date).astimezone(local_tz)
			
			past_games_grid.add_widget(Label(size_hint=(1, None), height=dp(60), font_name="PixeboyFont.ttf",
											 font_size=sp(20), text="{:02}/{:02}/{}  {:02}:{:02}:{:02}  -  {:<6}".
											 format(date.day, date.month, date.year, date.hour,
													date.minute, date.second, score)))


class GameScreen(Screen):
	"""
	The screen responsible for displaying the game, score and lives.
	Has no power over the actual game, from which it gets the data it needs to display.
	"""
	pass


class GameLayout(GridLayout):
	"""
	The layout for the GameScreen composed of the TopBar that displays the Score and Lives and
	the Game itself
	"""
	Lives = NumericProperty(3)
	Score = NumericProperty(0)
	
	def __init__(self, **kwargs):
		super(GameLayout, self).__init__(**kwargs)
		self.game = DownwardsGame()
		Clock.schedule_interval(self.update_frame, 1 / 60)
		Clock.schedule_once(self.create_game, 0)
	
	def create_game(self, _delta):
		""" Adds the game to the layout"""
		self.add_widget(self.game)
	
	def update_frame(self, delta):
		self.Lives, self.Score = self.game.update_frame(delta)


class DownwardsGame(Widget):
	"""
	The ShootTheBall Game in which the "Balls" come raining down from the top of the screen and will disappear
	when the user taps them or reach the bottom of the screen.
	"""
	
	def __init__(self, **kwargs):
		super(DownwardsGame, self).__init__(**kwargs)
		self.time_started = None
		self.lives = 3
		self.score = 0
		self.coins = 0
		self.level = 1
		self.started = False
		self.pre_game_menu = None
		self.menu_button_image = None
		self.start_button_image = None
		self.score_anti_overflow = False
		self.enemy_image = ""
		
		self.create_game()
	
	def get_enemy_image(self):
		self.enemy_image = self.parent.parent.manager.get_screen("shop").Skin
	
	def create_game(self):
		""" Creates the start button and go back to menu button"""
		self.pre_game_menu = BoxLayout(size_hint=(None, None), width=dp(240), height=dp(100), spacing=dp(40))
		start_button = Button(background_normal="", background_color=(0, 0, 0, 0))
		menu_button = Button(background_normal="", background_color=(0, 0, 0, 0))
		
		start_button.bind(on_release=self.start_game)
		menu_button.bind(on_release=self.go_to_menu)
		self.pre_game_menu.add_widget(start_button)
		self.pre_game_menu.add_widget(menu_button)
		
		self.pre_game_menu.pos = (
			self.width / 2 - self.pre_game_menu.width / 2, self.height / 2 - self.pre_game_menu.height / 2)
		self.add_widget(self.pre_game_menu)
		
		with start_button.canvas.after:
			self.start_button_image = Rectangle(size=start_button.size, source="images/StartButton.png")
		self.start_button_image.pos = self.pre_game_menu.x, self.pre_game_menu.y
		
		with menu_button.canvas.after:
			self.menu_button_image = Rectangle(size=menu_button.size, source="images/HomeButton.png")
		x, y = self.pre_game_menu.x + self.pre_game_menu.width / 2 + self.pre_game_menu.spacing / 2, self.pre_game_menu.y
		self.menu_button_image.pos = (x, y)
		
		self.start_button_image.size = self.menu_button_image.size = (dp(100), dp(100))
	
	def reset_game(self, _delta):
		""" Deletes all the balls on the screen and recreates the start and go back to menu buttons """
		# Reversing the children list so that we always delete the last element and do not skip any
		for child in self.children[::-1]:
			self.remove_widget(child)
		self.create_game()
	
	def on_size(self, _widget, _value):
		""" Repositions the start and go back to menu buttons in the middle of the widget"""
		if not self.started:
			self.pre_game_menu.pos = (
				self.width / 2 - self.pre_game_menu.width / 2, self.height / 2 - self.pre_game_menu.height / 2)
			
			self.start_button_image.pos = self.pre_game_menu.x, self.pre_game_menu.y
			x, y = self.pre_game_menu.x + self.pre_game_menu.width / 2 + self.pre_game_menu.spacing / 2, self.pre_game_menu.y
			self.menu_button_image.pos = (x, y)
			
			self.start_button_image.size = self.menu_button_image.size = (dp(100), dp(100))
	
	def start_game(self, widget):
		"""
		Resets the lives, score, and level and deletes the BoxLayout that contains the start and go
		back to menu button
		"""
	
		self.lives = 3
		self.score = 0
		self.coins = 0
		self.level = 1
		self.started = True
		self.time_started = datetime.datetime.utcnow()
		self.get_enemy_image()
		
		self.remove_widget(widget.parent)
	
	def go_to_menu(self, _widget):
		self.parent.parent.manager.current = "menu"
	
	def update_frame(self, delta):
		""" Updates the frame every 60th of a second and returns Lives and Score for the TopBar to display"""
		if self.started:
			while len(self.children) < 2 + self.level:
				ball = Ball(self.enemy_image, self.level)
				x = randint(0, int(self.width - ball.width))
				y = self.height - ball.height
				ball.pos = (x, y)
				
				self.add_widget(ball)
			
			time_factor = delta * 60
			for ball in self.children:
				ball.y -= ball.speed * time_factor
				if ball.shot:
					self.remove_widget(ball)
					if ball.is_coin:
						self.coins += 1
					else:
						self.score += self.level * 10
				
				# Progress to the next level and make sure it does that only one time
				# score_anti_overflow will make sure the level goes up only one time, it goes back to False once the\
				# user goes over Score 400
				next_level_score = sum([x * 1000 for x in range(1, self.level + 1)])
				
				if self.score > 0 and self.score % next_level_score == 0 and not self.score_anti_overflow:
					self.score_anti_overflow = True
					self.level += 1
				
				if self.score % next_level_score != 0:
					self.score_anti_overflow = False
				
				# Remove the ball if it goes out of bounds
				if ball.y + ball.height <= 0:
					self.remove_widget(ball)
					if not ball.is_coin:
						self.lives -= 1
					if self.lives == 0:
						self.started = False
						
						screen_manager = self.parent.parent.manager
						
						stat_screen = screen_manager.get_screen("stats")
						stat_screen.update_highscore(self.score)
						stat_screen.update_games_played()
						
						shop_screen = self.parent.parent.manager.get_screen("shop")
						shop_screen.Balance += self.coins
						
						stat_screen.update_db((self.time_started, self.score))
						stat_screen.update_games_played()
						Clock.schedule_once(self.reset_game, 1)
						
		return self.lives, self.score


class Ball(ButtonBehavior, Image):
	""" The Enemy that the player needs to tap in order to shoot it."""
	
	def __init__(self, image_source, level, **kwargs):
		super().__init__(**kwargs)
		self.speed = dp(randint(1 * level, 2 * level))
		self.shot = False
		self.is_coin = False
		self.source = image_source
		
		coin_chance = randint(1 * level, 10)
		if coin_chance <= 1 * level:
			self.source = "images/ShootTheBallsCoin.png"
			self.is_coin = True


class ShopScreen(Screen):
	Balance = NumericProperty(0)
	Skin = StringProperty("")
	
	def __init__(self, **kwargs):
		super(ShopScreen, self).__init__(**kwargs)
		Clock.schedule_once(self.update_skins, 0)
		self.skins_data = {}
		self.skins_file_store = JsonStore("skins.json")
		self.coins_store = JsonStore("coins.json")
		self.read_coins()
		Clock.schedule_interval(self.save_skins_data_time, 60)
		
	def read_coins(self):
		if self.coins_store.exists("coins"):
			self.Balance = self.coins_store.get("coins")["balance"]
		else:
			self.coins_store.put("coins", balance=0)
			
	def save_coins(self):
		self.coins_store["coins"] = {"balance": self.Balance}
	
	def on_Balance(self, _widget, _value):
		self.save_coins()
	
	def update_skins(self, dt):
		skins_filename = os.listdir("skins")
		skins_filename = sorted(skins_filename)
		skins = []
		for skin in skins_filename:
			if skin.endswith(".png"):
				self.skins_data[skin] = {
					"skin_name": skin,
					"price": 0,
					"owned": False,
					"selected": False,
				}
				skins.append(skin)
				
		self.retrieve_skins_data()
		
		def get_price(skin_elem):
			return self.skins_data[skin_elem]["price"]
		
		skins.sort(key=get_price)
		
		# The cheapest skin will always be owned and selected on launch, the selected skin will be changed later.
		self.skins_data[skins[0]]["owned"] = True
		if self.Skin == "":
			self.skins_data[skins[0]]["selected"] = True
			self.Skin = os.path.join("skins", skins[0])
		
		for skin in skins:
			s = Skin(skin)
			s.ids.skin_image.source = "skins/" + skin
			self.ids.skins_list.add_widget(s)
	
		for skin in self.ids.skins_list.children:
			skin.price = self.skins_data[skin.skin_name]["price"]
			skin.owned = self.skins_data[skin.skin_name]["owned"]
			skin.selected = self.skins_data[skin.skin_name]["selected"]
	
	def save_skins_data(self):
		for skin in self.skins_data.values():
			self.skins_file_store.put(skin["skin_name"], skin_name=skin["skin_name"], price=skin["price"],
									  owned=skin["owned"], selected=skin["selected"])
		self.save_skins_prices()
		
	def save_skins_data_time(self, dt):
		self.save_skins_data()
		
	def retrieve_skins_data(self):
		for skin_name in self.skins_file_store:
			self.skins_data[skin_name] = self.skins_file_store[skin_name]
			
			if self.skins_data[skin_name]["selected"] is True:
				self.Skin = os.path.join("skins", skin_name)
		self.retrieve_skins_prices()
			
	def save_skins_prices(self):
		with open("skins.csv", "w") as skins_prices:
			fieldnames = ("skin_name", "price")
			writer = csv.DictWriter(skins_prices, quoting=csv.QUOTE_MINIMAL, quotechar='"', delimiter='|',
									fieldnames=fieldnames)
			writer.writeheader()
			for skin_name in self.skins_data:
				writer.writerow({"skin_name": skin_name,
								 "price": self.skins_data[skin_name]["price"]})
				
	def retrieve_skins_prices(self):
		with open("skins.csv", "r") as skins_prices:
			reader = csv.DictReader(skins_prices, quoting=csv.QUOTE_MINIMAL, quotechar='"', delimiter='|')
			for row in reader:
				if row["skin_name"] in self.skins_data:
					self.skins_data[row["skin_name"]]["price"] = int(row["price"])
				else:
					print(f"Skin {row['skin_name']} Not Found")

	def set_menu_ball_skin(self):
		App.get_running_app().app_manager.get_screen("menu").bg_ball.source = self.Skin
		
	def on_Skin(self, widget, value):
		self.set_menu_ball_skin()


class Skin(ButtonBehavior, BoxLayout):
	def __init__(self, name, **kwargs):
		super(Skin, self).__init__(**kwargs)
		self.skin_name = name
		self.price = 0
		self.owned = False
		self.selected = False
		Clock.schedule_once(self.set_label, 0)
	
	@property
	def balance(self):
		return App.get_running_app().app_manager.get_screen("shop").Balance
	
	def set_label(self, dt):
		self.change_label()
	
	def select_skin(self):
		shop_screen = App.get_running_app().app_manager.get_screen("shop")
		
		for skin in self.parent.children:
			skin.selected = False
			skin.change_label()
			shop_screen.skins_data[skin.skin_name]["selected"] = False
		
		self.selected = True
		shop_screen.Skin = self.ids.skin_image.source
		shop_screen.skins_data[self.skin_name]["selected"] = True

	def on_release(self):
		if not self.owned:
			if self.balance >= self.price:
				App.get_running_app().app_manager.get_screen("shop").Balance = self.balance - self.price
				self.owned = True
				App.get_running_app().app_manager.get_screen("shop").skins_data[self.skin_name]["owned"] = True
				
				self.select_skin()
				self.change_label()
		else:
			if not self.selected:
				self.select_skin()
				self.change_label()
		
	def change_label(self):
		if self.selected:
			self.ids.skin_label.text = "SELECTED"
			self.ids.skin_label.color = get_color_from_hex("#00FF00")
			return
		elif self.owned:
			self.ids.skin_label.text = "OWNED"
			self.ids.skin_label.color = get_color_from_hex("#FFFFFF")
		else:
			self.ids.skin_label.text = "{:,} COINS".format(self.price)


class ShootTheBallsApp(App):
	def __init__(self, **kwargs):
		super(ShootTheBallsApp, self).__init__(**kwargs)
		self.app_manager = None
		self.stopped = False
		Builder.load_file("style.kv")
	
	def build(self):
		
		self.app_manager = AppManager()
		return self.app_manager
	
	def on_stop(self):
		if not self.stopped:
			self.stopped = True
			shop_screen = self.app_manager.get_screen("shop")
			shop_screen.save_skins_data()
			shop_screen.save_coins()
			

if __name__ == "__main__":
	ShootTheBallsApp().run()
