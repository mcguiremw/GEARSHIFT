import hashlib

x8664_args = ["VRDI", "VRSI", "VRDX", "VRCX"]

struct_hashes = {}

n = 0

# gets the struct modifier based on member type and size
def get_modifier(member):
	if type(member[0]) is int:
		if member[1] == 4:
			return "int"
		elif member[1] == 8:
			return "long"
	elif type(member[0]) is Struct:
		return str(member[0]) + "*"

# A struct is defined by a name, id in the order of creation, and offsets of members
# The class's members list store values and/or pointer to structs with the size of each member
# insert_member consolidates current member list if necessary to insert a new member
# get_struct_at_off fetches the struct pointer member at some offset
class Struct:
	def __init__(self, name, offsets, id):
		print("Create", name, offsets)
		self.name = name
		self.members = []
		self.id = id
		for i in range(len(offsets) - 1):
			member_length = offsets[i + 1] - offsets[i]
			self.members.append((0x0, member_length))
		self.members.append((0x0, 8))

	def insert_member(self, member_size, offset, value):
		print("Inserting", member_size, offset, "into", self.name, self.members)
		c = 0
		length = 0
		while length < offset:
			length += self.members[c][1]
			c += 1
		if length != offset:
			raise Exception("Offset mismatch")
		replace = 0
		while replace < member_size:
			replace += self.members[c][1]
			del self.members[c]
		self.members.insert(c, (value, member_size))

	def __str__(self):
		return self.name + str(self.id)

	def get_struct_at_off(self, offset):
		print("fetch struct at off", self.name, offset, self.members)
		c = 0
		length = 0
		while length < offset:
			length += self.members[c][1]
			c += 1
		ret = self.members[c][0]
		if type(ret) is int:
			raise Exception("Dereference is primitive")
		return ret

	def pp(self):
		print(self.members)
		print("struct " + str(self) + " {")
		for i in range(len(self.members)):
			cur = struct.members[i]
			print("\t" + get_modifier(cur) + " entry_" + str(i) + ";")
		print("}")
	
	def get_hash(self):
		h = 0
		for i in range(len(self.members)):
			if self.members[i][0] == 0:
				h = 31 * h + self.members[i][1]
			else:
				h = 31 * h + (int(hashlib.md5(str(self.members[i][0]).encode()).hexdigest(), 16) & 0xff)
		return h

# finds the depth of a struct description key
def get_depth(key, depth):
	idx = key.find("(")
	if idx == -1:
		return depth + 1
	name = key[:idx + 1]
	child = key[idx + 1:]
	return depth + get_depth(child, depth) + 1

def get_member_length(name):
	if name.startswith("V"):
		return 8
	elif name.startswith("W"):
		return 4

# parses a key for top level name, child descriptor key, and child offset
def parse_key(key):
	start = key.find("(")
	end = len(key) + 1
	if start == -1:
		off = 0
		if "+" in key:
			start = key.find("+")
			off = int(key[start + 1:])
		else:
			start = len(key) + 1
		return key[:start], off, ""
	else:
		end = len(key) - key[::-1].find(")")
	name = key[:start]
	offset = 0
	child = key[start + 1:end - 1]
	off = key[end:]
	if len(off) != 0:
		offset = int(off)	
	print(key, name, offset, child)
	return name, offset, child

# finds the struct a descriptor key is referring to by propagation from the lowest level up and dereferencing the struct at some offset at each level until it reaches the top
def find_struct(key, arguments):
	name, offset, child = parse_key(key)
	if len(child) == 0:
		return arguments[name], offset
	else:
		child_struct, child_struct_offset = find_struct(child, arguments)
		return child_struct.get_struct_at_off(child_struct_offset), offset

# builds a struct for the current descriptor key
def build_struct(tup, arguments):
	key = tup[1]
	offsets = tup[2]

	name, offset, child = parse_key(key)

	# TODO: find duplicate struct signature
	global n
	struct = Struct(name, offsets, n)
	if struct.get_hash() in struct_hashes:
		struct = struct_hashes[struct.get_hash()]
	n += 1
	arguments[name] = struct
	struct_hashes[struct.get_hash()] = struct

	if len(child) > 0:
		child_struct, offset = find_struct(child, arguments)
		print(child, offset)
		child_struct.insert_member(get_member_length(name), offset, struct)
	return struct

# structs is a list of tuples of the form (key, Offsets)
# this returns a list of structs
def converter(structs, num_args):
	arguments = {}
	depth_sorted = []
	result = []
	# assign recursive struct depth to each key
	for i in range(len(structs)):
		key = structs[i][0]
		offsets = structs[i][1]
		depth = get_depth(key, 0)
		depth_sorted.append((depth, key, offsets))
	depth_sorted.sort()
	for i in range(len(depth_sorted)):
		# parse and create structs
		struct = build_struct(depth_sorted[i], arguments)
		result.append(struct)
	return result

structs = [("V(V(VRDI+8)+24)", [0, 4, 8, 12]), ("V(V(VRDI+8)+16)", [0, 4, 8, 12]), ("V(VRDI+8)", [0, 8, 16, 24]), ("VRDI", [0, 4, 8])]
num_args = 1
res = converter(structs, num_args)
for struct in res:
	struct.pp()
