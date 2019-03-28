class Calculation(object):
    @staticmethod
    def make_ints(*args):
        try:
            return [int(arg) for arg in args]
        except ValueError:
            raise TypeError("Couldn't coerce arguments to integers: {}".format(*args))

    def add(self, a, b):
        a, b = self.make_ints(a, b)
        return a + b

    def subtract(self, a, b):
        a, b = self.make_ints(a, b)
        return a - b

    def multiply(self, a, b):
        a, b = self.make_ints(a, b)
        return a * b

    def divide(self, a, b):
        a, b = self.make_ints(a, b)
        return a // b
