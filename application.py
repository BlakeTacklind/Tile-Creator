
import argparse
import json

def prettyPrint(data):
	print(json.dumps(data, sort_keys=True, indent=4, separators=(',', ': ')))

minX = None
maxX = None
minY = None
maxY = None

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

def updatePoints(point):
	# print(point)
	global minX, maxX, minY, maxY
	minX = minSpecial(minX, point['x'])
	minY = minSpecial(minY, point['y'])
	maxX = maxSpecial(maxX, point['x'])
	maxY = maxSpecial(maxY, point['y'])

def isWall(layer):
	return "wall" in layer["name"]

def readDPS(filename):
	with open(filename) as file:
		data = json.loads("".join(file))

	# get edges of map
	for objectTypes in data["tables"]:
		for obj in data["tables"][objectTypes]:
			if "points" in obj:
				for point in obj["points"]:
					updatePoints(point)

	global walls
	walls = []
	for layer in data["tables"]["Layer"]:
		if isWall(layer):
			out = [x for x in data["tables"]["Wall"] if x['id'] == layer["data"]]
			if len(out) != 1:
				raise Exception("A bad number of walls! "+str(len(out)))

			walls.append(Wall(out[0]))

def getRelativePoints(point):
	return {'x': point['x'] - minX, 'y': maxY - point['y']}

def convertPoint(pnt):
	return str((pnt['x'] - (maxX - minX) / 2) * RATIO)+","+str((pnt['y'] - (maxY - minY) / 2) * RATIO)

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
		return "\n</occluder>\n"


class Wall(Occluder):
	"""docstring for Wall"""
	def __init__(self, arg):
		super(Wall, self).__init__()
		self.points = list(map(getRelativePoints, arg["points"]))
		self.thickness = arg["thickness"]

	def getXMLPoints(self):
		return "<points>"+",".join(map(convertPoint, self.points))+"</points>"

	def __str__(self):
		return self.getXMLStart()+self.getXMLPoints()+self.getXMLEnd()

def xmlStart():
	return "<root>\n<occluders>\n"
def xmlEnd():
	return "</occluders>\n</root>\n"

def createXML(output):
	xmlString = xmlStart()
	for wall in walls:
		xmlString += str(wall)
	xmlString += xmlEnd()

	with open(output, "w") as file:
		file.write(xmlString)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("input", help="input DPS file")
	parser.add_argument("output", help="output xml file")
	parser.add_argument("-r", dest="RATIO", default=100,
		help="set the number of pixels per square")
	args = parser.parse_args()

	global RATIO
	RATIO = args.RATIO
	readDPS(args.input)

	createXML(args.output)
