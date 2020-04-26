
import argparse
import json
import math
import itertools

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("input", help="input DPS file")
	parser.add_argument("output", help="output xml file")
	parser.add_argument("-r", dest="RATIO", default=100,
		help="set the number of pixels per square")
	parser.add_argument("-t", dest="THICC", action='store_const', default=True,
		const=False, help="Make walls a single line thin")
	parser.add_argument("-p", dest="PP", action='store_const', default=False,
		const=True, help="Just pretty print json")
	global args
	args = parser.parse_args()

	readDPS(args.input)

	createXML(args.output)

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
		if args.THICC:
			return self.getComplexXML()
		else:
			return self.getSimpleXML()

	def getComplexXML(self):
		result = ""
		for a,b in pairwise(self.points):
			# try:
			occ = Occluder()
			box = makeBox(a, b, self.thickness/10)
			if box:
				result += occ.getXMLStart()+self.getSimpleXMLPoints(makeBox(a, b, self.thickness/10))+occ.getXMLEnd()
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
	return "{:.2f},{:.2f}".format((pnt['x'] - (maxX - minX) / 2) * args.RATIO, (pnt['y'] - (maxY - minY) / 2) * args.RATIO)

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

		box = makeBox(addVector(self.position, -a, -b), x, 0.1 * self.scale)
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
			result += occ.getXMLStart()+self.getSimpleXMLPoints(makeBox(a, b, self.thickness/10))+self.doorXMLtag()+occ.getXMLEnd()
		return result

	def doorXMLtag(self):
		return "<secret>true</secret>\n"

	@staticmethod
	def isSecret(layer):
		return layer["name"].startswith("secret") or layer["name"].startswith("Secret")

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
