from fpdf import FPDF
import subprocess
import math


slant_color = (240, 240, 240)
main_line_color = (0, 0, 0)
checkers_color = (0, 0, 0)
secondary_line_color = (200, 200, 200)


class Point:
	def __init__(self, x, y):
		self.x = x;
		self.y = y;

	def __add__(a, b):
		return Point(a.x + b.x, a.y + b.y)

	def __str__(self):
		return '({}, {})'.format(self.x, self.y)


class Rect:
	def __init__(self, size, top_left):
		self.size = size
		self.top_left = top_left
		self.top_right = Point(top_left.x + size.x, top_left.y)
		self.bottom_right = Point(top_left.x + size.x, top_left.y + size.y)
		self.bottom_left = Point(top_left.x, top_left.y + size.y)

		self.left = self.top_left.x
		self.right = self.bottom_right.x
		self.top = self.top_left.y
		self.bottom = self.bottom_right.y


class LineConfiguration:
	def __init__(self, nib_width, ascender_logical_height=2, x_logical_height=4, descender_logical_height=2, space_logical_height=1, slant_lines_angle=45, slant_lines_logical_spacing=10, letter_direction_angle=90, letter_direction_logical_spacing=10):
		self.nib_width = nib_width
		self.ascender_logical_height = ascender_logical_height
		self.x_logical_height = x_logical_height
		self.descender_logical_height = descender_logical_height
		self.space_logical_height = space_logical_height
		self.slant_lines_angle = slant_lines_angle * 2.0 * math.pi / 360.0
		self.slant_lines_logical_spacing = slant_lines_logical_spacing
		self.letter_direction_angle = letter_direction_angle * 2.0 * math.pi / 360.0
		self.letter_direction_logical_spacing = letter_direction_logical_spacing

		self.ascender_line_offset = 0
		self.height_line_offset = self.ascender_line_offset + nib_width * ascender_logical_height
		self.base_line_offset = self.height_line_offset + nib_width * x_logical_height
		self.descender_line_offset = self.base_line_offset + nib_width * descender_logical_height

	def full_height(self):
		return self.descender_line_offset + self.space_height();

	def line_height(self):
		return self.descender_line_offset;

	def space_height(self):
		return self.space_logical_height * self.nib_width

	def slant_lines_spacing(self):
		return self.slant_lines_logical_spacing * self.nib_width

	def letter_direction_spacing(self):
		return self.letter_direction_logical_spacing * self.nib_width

class PageConfiguration:
	def __init__(self, orientation, page_format, margin):
		self.orientation = orientation
		self.page_format = page_format
		self.margin = margin


class PageContext:
	def __init__(self, config):
		self.page_configuration = config
		self.fpdf = FPDF(config.orientation, 'mm', config.page_format)

		size = Point(self.fpdf.w - 2 * config.margin, self.fpdf.h - 2 * config.margin)
		top_left = Point(config.margin, config.margin)
		self.working_area = Rect(size, top_left)

	def draw_horizontal_line(self, y, color):
		self.set_color(color)
		self.fpdf.line(self.working_area.left, self.working_area.top + y, self.working_area.right, self.working_area.top + y)

	def draw_slant_line(self, angle, bottom_left, max_height):
		bottom_left += self.working_area.top_left

		max_width = self.working_area.right - bottom_left.x
		tan_angle = math.tan(angle)
		width = max_height / tan_angle
		width = min(width, max_width)
		height = width * tan_angle
		top_right_offset = Point(width, -height)

		top_right = bottom_left + top_right_offset
		self.set_color(slant_color)
		self.fpdf.line(bottom_left.x, bottom_left.y, top_right.x, top_right.y)

	def draw_square(self, y, size, has_offset):
		width = 0.25 * size
		x = self.working_area.left
		if has_offset:
			x += width
		self.fpdf.rect(x, self.working_area.top + y, width, size, 'F')

	def set_color(self, color):
		self.fpdf.set_draw_color(color[0], color[1], color[2])

	def draw_debug_layout(self):
		self.set_color((0, 0, 0))
		area = self.working_area
		tl = area.top_left
		tr = area.top_right
		br = area.bottom_right
		bl = area.bottom_left
		self.fpdf.line(tl.x, tl.y, br.x, br.y)
		self.fpdf.line(bl.x, bl.y, tr.x, tr.y)
		self.fpdf.rect(tl.x, tl.y, area.size.x, area.size.y, 'D')


class Generator:
	def __init__(self, page_configuration):
		self.page_context = PageContext(page_configuration)

	def add_page(self, line_configuration):
		self.page_context.fpdf.add_page()

		space_height = line_configuration.space_height()
		line_height = line_configuration.line_height()
		available_height = self.page_context.working_area.size.y
		number_of_lines = int((available_height - space_height) / line_configuration.full_height());

		layout_height = number_of_lines * line_height + (number_of_lines - 1) * space_height
		layout_offset = (available_height - layout_height) * 0.5

		for i in range(number_of_lines):
			self.draw_line_layout(line_configuration, layout_offset + i * line_configuration.full_height())

		# self.page_context.draw_debug_layout()

	def draw_line_layout(self, line_configuration, top_y):
		number_of_slants = int(self.page_context.working_area.size.x / line_configuration.slant_lines_spacing())
		for i in range(number_of_slants):
			self.page_context.draw_slant_line(line_configuration.slant_lines_angle, Point(line_configuration.slant_lines_spacing() * i, top_y + line_configuration.descender_line_offset), line_configuration.line_height())

		number_of_letter_directions = int(self.page_context.working_area.size.x / line_configuration.letter_direction_spacing())
		for i in range(number_of_letter_directions):
			self.page_context.draw_slant_line(line_configuration.letter_direction_angle, Point(line_configuration.letter_direction_spacing() * i, top_y + line_configuration.descender_line_offset), line_configuration.line_height())

		self.page_context.set_color(checkers_color)
		squares_drawn = 0
		squares_drawn += self.draw_checkers(line_configuration, top_y + line_configuration.ascender_line_offset, line_configuration.ascender_logical_height, squares_drawn)
		squares_drawn += self.draw_checkers(line_configuration, top_y + line_configuration.height_line_offset, line_configuration.x_logical_height, squares_drawn)
		squares_drawn += self.draw_checkers(line_configuration, top_y + line_configuration.base_line_offset, line_configuration.descender_logical_height, squares_drawn)
		
		self.page_context.draw_horizontal_line(top_y + line_configuration.ascender_line_offset, secondary_line_color)
		self.page_context.draw_horizontal_line(top_y + line_configuration.height_line_offset, main_line_color)
		self.page_context.draw_horizontal_line(top_y + line_configuration.base_line_offset, main_line_color)
		self.page_context.draw_horizontal_line(top_y + line_configuration.descender_line_offset, secondary_line_color)

	def draw_checkers(self, line_configuration, y, count, squares_drawn):
		for i in range(count):
			self.page_context.draw_square(y + i * line_configuration.nib_width, line_configuration.nib_width, (squares_drawn + i) % 2 == 1)
		return count

	def save(self, path):
		self.page_context.fpdf.output(path, 'F')


def generate_page(page_configuration, line_configuration):
	gen = Generator(page_configuration)
	gen.add_page(line_configuration)
	filename = 'worksheet_{}mm_{}-{}-{}.pdf'.format(line_configuration.nib_width, line_configuration.ascender_logical_height, line_configuration.x_logical_height, line_configuration.descender_logical_height)
	gen.save(filename)
	print('Worksheet saved to "{}"'.format(filename))


def main():
	page_configuration = PageConfiguration(orientation='L', page_format='A4', margin=5)
	line_configurations = [
		LineConfiguration(3.8, space_logical_height=0.5),
		LineConfiguration(6, space_logical_height=0.2),
	]

	for line_configuration in line_configurations:
		generate_page(page_configuration, line_configuration)


if __name__ == '__main__':
	main()
