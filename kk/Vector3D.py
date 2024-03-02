class Vector3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return f"Vector3D({self.x}, {self.y}, {self.z})"

    def norm(self):
        from math import sqrt
        return sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return Vector3D(self.y * other.z - self.z * other.y,
                        self.z * other.x - self.x * other.z,
                        self.x * other.y - self.y * other.x)

    @staticmethod
    def are_orthogonal(vector1, vector2):
        return vector1.dot(vector2) == 0


v1 = Vector3D(1, 2, 3)
v2 = Vector3D(4, 5, 6)
v3 = v1 + v2  
v4 = v1 - v2  
v5 = v1 * 2   
norm_v1 = v1.norm()  
dot_product = v1.dot(v2)  
cross_product = v1.cross(v2) 
are_orthogonal = Vector3D.are_orthogonal(v1, v2)  

(v1, v2, v3, v4, v5, norm_v1, dot_product, cross_product, are_orthogonal)
