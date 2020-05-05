
import argparse
import json
import math
import itertools
import os

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("input", help="input DPS file")
	parser.add_argument("-o", dest="output", help="output xml file")
	parser.add_argument("-f", dest="Folder", type=str,
		help="output folder name. Just use the same basename")
	parser.add_argument("-r", dest="RATIO", default=100,
		help="set the number of pixels per square")
	parser.add_argument("-t", dest="THICC", default=1, type=float,
		help="change ratio of wall thickness. 0 is for just a line. 1 is for default thickness")
	parser.add_argument("-p", dest="PP", action='store_const', default=False,
		const=True, help="Just pretty print json (for debugging)")
	parser.add_argument("--trees", dest="TREES", action='store_const', default=False,
		const=True, help="Find and create terrain around trees")
	parser.add_argument("-x", dest="SHIFT_X", default=0, type=int,
		help="Shift the placement of items in the x direction by n pixels")
	parser.add_argument("-y", dest="SHIFT_Y", default=0, type=int,
		help="Shift the placement of items in the y direction by n pixels")
	global args
	args = parser.parse_args()

	if args.output is None and args.Folder is None:
		raise Exception("Need either -o or -f option")

	if args.THICC < 0:
		raise Exception("thickness needs to be a positive number")

	readDPS(args.input)

	if args.output is not None:
		createXML(args.output)

	if args.Folder is not None:
		#unclear why a the srting ends with a quote sometimes
		if args.Folder.endswith("\""):
			args.Folder = args.Folder[:-1]

		dropped_extention = os.path.basename(args.input).split(".")[0]
		output = os.path.join(args.Folder, dropped_extention)+".xml"
		createXML(output)

def readDPS(filename):
	with open(filename) as file:
		global data
		data = json.loads("".join(file))

	if args.PP:
		prettyPrint(data)
		exit(0)

	# get edges of map
	for objectTypes in data["tables"]:
		for obj in data["tables"][objectTypes]:
			if "points" in obj:
				for point in obj["points"]:
					updatePoints(point)

	global walls
	walls = []
	for layer in data["tables"]["Layer"]:
		if Wall.isWall(layer):
			walls.append(Wall(findData(layer["data"], data["tables"]["Wall"])))

	global doors
	doors = []
	for layer in data["tables"]["Layer"]:
		if Door.isDoor(layer):
			doors.append(Door(layer, findData(layer["data"], data["tables"]["Obstacle"])))
 
	global secrets
	secrets = []
	for layer in data["tables"]["Layer"]:
		if Secret.isSecret(layer):
			secrets.append(Secret(findData(layer["data"], data["tables"]["Wall"])))

	if args.TREES:
		global trees
		trees = []
		for layer in data["tables"]["Layer"]:
			if TreeTerrain.isRound(layer):
				trees.append(TreeTerrain(layer, findData(layer["data"], data["tables"]["Obstacle"])))

		global columns
		columns = []
		for layer in data["tables"]["Layer"]:
			if Column.isRound(layer):
				columns.append(Column(layer, findData(layer["data"], data["tables"]["Obstacle"])))

def findData(id, table):
	out = [x for x in table if x['id'] == id]
	if len(out) != 1:
		raise Exception("A bad number of walls! "+str(len(out)))

	return out[0]


def createXML(output):
	xmlString = xmlStart()
	for wall in walls:
		xmlString += wall.getXML()
	for door in doors:
		xmlString += door.getXML()
	for secret in secrets:
		xmlString += secret.getXML()

	if args.TREES:
		for tree in trees:
			xmlString += tree.getXML()
		for column in columns:
			xmlString += column.getXML()

	xmlString += xmlEnd()

	with open(output, "w") as file:
		file.write(xmlString)

def xmlStart():
	return "<root>\n<occluders>\n"
def xmlEnd():
	return "</occluders>\n</root>\n"

class Wall(object):
	"""docstring for Wall"""
	def __init__(self, arg):
		super(Wall, self).__init__()
		self.points = list(map(getRelativePoints, arg["points"]))
		self.thickness = arg["thickness"]

	def getSimpleXMLPoints(self, points):
		return "<points>"+",".join(map(convertPoint, points))+"</points>\n"

	def getXML(self):
		if args.THICC == 0:
			return self.getSimpleXML()
		else:
			return self.getComplexXML()

	def getComplexXML(self):
		result = ""
		for a,b in pairwise(self.points):
			occ = Occluder()
			box = makeBox(a, b, self.thickness / 10 * args.THICC)
			if box:
				result += occ.getXMLStart()+self.getSimpleXMLPoints(box)+occ.getXMLEnd()
		return result

	def getSimpleXML(self):
		occ = Occluder()
		return occ.getXMLStart()+self.getSimpleXMLPoints(self.points)+occ.getXMLEnd()

	@staticmethod
	def isWall(layer):
		return layer["name"].startswith("wall")

def getRelativePoints(point):
	return {'x': point['x'] - minX, 'y': maxY - point['y']}

def convertPoint(pnt):
	#move 0,0 to middle of the image and adjust from cell based to pixel based quardinates
	return "{:.2f},{:.2f}".format((pnt['x'] - (maxX - minX) / 2) * args.RATIO + args.SHIFT_X, (pnt['y'] - (maxY - minY) / 2) * args.RATIO + args.SHIFT_Y)

class Door(object):
	"""docstring for Door"""
	def __init__(self, layer, data):
		super(Door, self).__init__()
		#is it a double door
		self.double = "double" in layer["name"]
		#get angle in radians
		self.angle = -data["angle"] / 180 * math.pi
		self.scale = data["scale"]

		self.position = addVector(getRelativePoints(data["begin"]), self.scale/2*math.sin(self.angle), -self.scale/2*math.cos(self.angle))

	def getXMLPoints(self):
		unit = self.scale / 2

		a = unit * math.cos(self.angle)
		b = unit * math.sin(self.angle)

		if not self.double:
			x = addVector(self.position, a, b)
		else:
			#double doors just extend out in one direction
			#since vector (a,b) is a half the lenth of a
			#single door, triple it
			x = addVector(self.position, a*3, b*3)

		box = makeBox(addVector(self.position, -a, -b), x, 0.1 * self.scale * args.THICC)
		return "<points>"+",".join(map(convertPoint, box))+"</points>\n"

	def getXML(self):
		occ = Occluder()
		return occ.getXMLStart()+self.getXMLPoints()+self.doorXMLtag()+occ.getXMLEnd()

	def doorXMLtag(self):
		return "<door>true</door>\n"

	@staticmethod
	def isDoor(layer):
		return "door" in layer["name"]

class Secret(Wall):
	"""docstring for Secret"""
	def __init__(self, arg):
		super(Secret, self).__init__(arg)

	def getXML(self):
		result = ""
		for a,b in pairwise(self.points):
			occ = Occluder()
			result += occ.getXMLStart()+self.getSimpleXMLPoints(makeBox(a, b, self.thickness / 10 * args.THICC))+\
			self.doorXMLtag()+occ.getXMLEnd()
		return result

	def doorXMLtag(self):
		return "<secret>true</secret>\n"

	@staticmethod
	def isSecret(layer):
		return layer["name"].startswith("secret") or layer["name"].startswith("Secret")

class TreeTerrain(object):
	"""docstring for TreeTerrain"""
	def __init__(self, layer, data):
		self.small = "small" in layer["name"]
		self.mid = "mid" in layer["name"]
		self.big = "big" in layer["name"]
		self.angle = -data["angle"] / 180 * math.pi
		self.scale = data["scale"]

		if self.mid:
			#middle sized trees have their center point offset from the
			#image's center
			v = {'x': self.scale / 2, 'y': self.scale / 2}
			v = rotateVector(v, self.angle)
			self.position = getRelativePoints(addVector((data["begin"]), v['x'], v['y']))
		else:
			self.position = getRelativePoints(data["begin"])

	def getXML(self):
		occ = Occluder()
		return occ.getXMLStart()+self.getXMLPoints()+self.terrainXMLtag()+occ.getXMLEnd()

	def terrainXMLtag(self):
		return "<terrain>true</terrain>\n"

	def getXMLPoints(self):
		return "<points>"+",".join(map(convertPoint, self.makeShape()))+"</points>\n"

	def makeShape(self):
		dist = self.scale / 2

		if self.small:
			dist /= 2
		if self.mid:
			dist /= 1.5

		return drawCircle(self.position, dist/2)

	@staticmethod
	def isRound(layer):
		return "tree" in layer["name"]

class Column(object):
	"""docstring for Column"""
	def __init__(self, layer, data):
		self.angle = -data["angle"] / 180 * math.pi
		self.scale = data["scale"]

		self.position = getRelativePoints(data["begin"])

	def getXML(self):
		occ = Occluder()
		return occ.getXMLStart()+self.getXMLPoints()+occ.getXMLEnd()

	def getXMLPoints(self):
		return "<points>"+",".join(map(convertPoint, self.makeShape()))+"</points>\n"

	def makeShape(self):
		return drawCircle(self.position, self.scale / 2, close=True)

	@staticmethod
	def isRound(layer):
		return "column" in layer["name"]

def drawCircle(point, radius, steps=8, close=False):
	vect = {'x':radius, 'y':0}

	points = []
	for step in range(steps):
		angle = 2 * math.pi / steps * step
		v = rotateVector(vect, angle)
		points.append(addVector(point, v['x'], v['y']))

	if close:
		points.append(addVector(point, vect['x'], vect['y']))

	return points


def rotateVector(vect, angle):
	return {
		'x': math.cos(angle) * vect['x'] - math.sin(angle) * vect['y'],
		'y': math.sin(angle) * vect['x'] + math.cos(angle) * vect['y']
	}

class Occluder(object):
	ID = 1
	"""docstring for Occluder"""
	def __init__(self):
		super(Occluder, self).__init__()
		self.id = Occluder.ID
		Occluder.ID += 1

	def getXMLStart(self):
		return f"<occluder>\n<id>{self.id}</id>\n"

	def getXMLEnd(self):
		return "</occluder>\n"

def makeBox(pointA, pointB, thickness=0.1):
	#make a box from a vector
	#https://math.stackexchange.com/questions/60336/how-to-find-a-rectangle-which-is-formed-from-the-lines

	dist = math.sqrt(math.pow(pointB['x'] - pointA['x'], 2) + math.pow(pointB['y'] - pointA['y'], 2))
	if dist == 0:
		return []
	ajustmentX = (pointB['y'] - pointA['y']) / dist * thickness
	ajustmentY = (pointA['x'] - pointB['x']) / dist * thickness

	return [
		addVector(pointA, ajustmentX, ajustmentY),
		addVector(pointA, -ajustmentX, -ajustmentY),
		addVector(pointB, -ajustmentX, -ajustmentY),
		addVector(pointB, ajustmentX, ajustmentY),
		addVector(pointA, ajustmentX, ajustmentY)
	]

def addVector(point, x, y):
	return {'x':point['x'] + x, 'y':point['y'] + y}

def pairwise(iterable):
    #s -> (s0,s1), (s1,s2), (s2, s3), ...
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)  

minX = None
maxX = None
minY = None
maxY = None

def updatePoints(point):
	# print(point)
	global minX, maxX, minY, maxY
	minX = minSpecial(minX, point['x'])
	minY = minSpecial(minY, point['y'])
	maxX = maxSpecial(maxX, point['x'])
	maxY = maxSpecial(maxY, point['y'])

def minSpecial(a, b):
	if a is None:
		return b
	else:
		return min(a, b)

def maxSpecial(a, b):
	if a is None:
		return b
	else:
		return max(a, b)

def prettyPrint(data):
	print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

if __name__ == "__main__":
	main()
