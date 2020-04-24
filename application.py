
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
	global args
	args = parser.parse_args()

	# prettyPrint(args.input)

	readDPS(args.input)

	createXML(args.output)

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


def createXML(output):
	xmlString = xmlStart()
	for wall in walls:
		xmlString += wall.getXML()
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
		return "<points>"+",".join(map(convertPoint, points))+"</points>"

	def getXML(self):
		if args.THICC:
			return self.getComplexXML()
		else:
			return self.getSimpleXML()

	def getComplexXML(self):
		result = ""
		for a,b in pairwise(self.points):
			occ = Occluder()
			result += occ.getXMLStart()+self.getSimpleXMLPoints(makeBox(a, b, self.thickness/10))+occ.getXMLEnd()
		return result

	def getSimpleXML(self):
		occ = Occluder()
		return occ.getXMLStart()+self.getSimpleXMLPoints(self.points)+occ.getXMLEnd()

def getRelativePoints(point):
	return {'x': point['x'] - minX, 'y': maxY - point['y']}

def convertPoint(pnt):
	#move 0,0 to middle of the image and adjust from cell based to pixel based quardinates
	return str((pnt['x'] - (maxX - minX) / 2) * args.RATIO)+","+str((pnt['y'] - (maxY - minY) / 2) * args.RATIO)


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

	# def getXML(self, points):
	# 	pass

def makeBox(pointA, pointB, thickness=0.1):
	#make a box from a vector
	#https://math.stackexchange.com/questions/60336/how-to-find-a-rectangle-which-is-formed-from-the-lines

	dist = math.sqrt(math.pow(pointB['x'] - pointA['x'], 2) + math.pow(pointB['y'] - pointA['y'], 2))
	# normal = (pointB['y'] - pointA['y'], pointA['x'] - pointB['x'])
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
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)  

def isWall(layer):
	return "wall" in layer["name"]

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
