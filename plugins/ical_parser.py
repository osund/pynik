from __future__ import with_statement
import re
import utility
import datetime
from commands import Command

class Event:
	def __init__(self):
		self.start = None
		self.end = None
		self.summary = None
		self.location = None

	def short_description(self):
		return "%s-%s %s: %s" % (self.start.strftime("%H:%M"), self.end.strftime("%H:%M"), self.location, self.summary)

	def long_description(self):
		return "%s-%s %s: %s" % (self.start.strftime("%a %d %b %H:%M"), self.end.strftime("%H:%M"), self.location, self.summary)

	def __str__(self):
		return self.long_description()

class iCalParser:
	def __init__(self):
		self.event = None
		self.events = []

	def parse_begin(self, tag, argument):
		if tag == "VEVENT":
			self.event = Event()

	def parse_end(self, tag, argument):
		if tag == "VEVENT":
			if self.event.end > datetime.datetime.now():
				self.events.append(self.event)
			self.event = None

	def parse(self, tag, argument, extra_argument):
		argument = argument.replace("\,", ",")

		if tag == "BEGIN":
			self.parse_begin(argument, extra_argument)
		elif tag == "END":
			self.parse_end(argument, extra_argument)
		elif self.event:
			if tag == "DTSTART":
				self.event.start = datetime.datetime.strptime(argument, "%Y%m%dT%H%M%S")
			elif tag == "DTEND":
				self.event.end = datetime.datetime.strptime(argument, "%Y%m%dT%H%M%S")
			elif tag == "SUMMARY":
				self.event.summary = ", ".join(argument.split(", ")[0:2])
			elif tag == "LOCATION":
				self.event.location = argument
		#print tag, argument, extra_argument

	def process(self, data):
		pattern = re.compile("(.+?)(;(.+))?:(.+)")
		for line in data.split("\r\n"):
			m = pattern.match(line)
			if m:
				tag, junk, extra_argument, argument = m.groups()
				self.parse(tag, argument, extra_argument)

		return None

class Schema(Command):
	id_presets = {}
	id_directory = {}

	def __init__(self):
		pass

	def trig_schema(self, bot, source, target, trigger, argument):
		if not argument:
			argument = self.id_presets.get(source.lower(), source.lower())
		else:
			argument = argument.lower()
			self.id_presets[source.lower()] = argument
			self.save()

		if argument in self.id_directory:
			url = self.id_directory[argument]
			if isinstance(url, int):
				url = "http://timeedit.liu.se/4DACTION/iCal_downloadReservations/timeedit.ics?branch=5&id1=%d&lang=1" % url
			
			response = utility.read_url(url)

			parser = iCalParser()
			parser.process(response["data"])

			relevant_events = parser.events[0:5]
			event_outputs = []
			last_event = None
			for event in relevant_events:
				if last_event and last_event.start.day == event.start.day:
					event_outputs.append(event.short_description())
				else:
					event_outputs.append(event.long_description())
					
				last_event = event

			return "%s: %s" % (argument, " | ".join(event_outputs))
		else:
			return "I don't have the ID '" + argument + "' in my directory. Feel free to add it by typing .addschemaid <name> <url or timeedit id>."

	def trig_addschemaid(self, bot, source, target, trigger, argument):
		m_num = re.match('(\S+)\s+(\d+)', argument)
		m_url = re.match('(\S+)\s+((https?:\/\/|www.)\S+)', argument)
		
		if m_num:
			name, num = m_num.groups()
			self.id_directory[name.lower()] = int(num)
			self.save()
			return "Added %s." % name.lower()
			
		elif m_url:
			name = m_url.group(1)
			url = m_url.group(1)
			self.id_directory[name.lower()] = url
			self.save()
			return "Added %s." % name.lower()
			
		else:
			return "Try .addschemaid <name> <url or timeedit id>"

	def save(self):
		utility.save_data('schema_id', self.id_directory)
		utility.save_data('schema_fav', self.id_presets)

	def on_load(self):
		self.id_directory = utility.load_data('schema_id')
		if not self.id_directory:
			self.id_directory = {}
			
		self.id_presets = utility.load_data('schema_fav')
		if not self.id_presets:
			self.id_presets = {}

