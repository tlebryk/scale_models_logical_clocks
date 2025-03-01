class LamportClock:
    def __init__(self, name):
        self.name = name
        self.value = 0

    def increment(self):
        self.value += 1

    def compare(self, clock_value):
        self.value = max(self.value, clock_value) + 1

    def __str__(self):
        return f"{self.name}: {self.value}"
