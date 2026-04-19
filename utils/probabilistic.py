# alpha controls how much we trust new readings
# 0.3= cautious (trust prior more), 0.7 = aggressive (trust sensor more)

# Example: prior = 70 cars, sensor says 90 cars
# new_belief = 0.3 * 90 + 0.7 * 70 = 27 + 49 = 76 cars
# More cautious than jumping straight to 90
def bayesian_update(prior, sensor_reading, alpha=0.3):
    new_belief = alpha * sensor_reading + (1 - alpha) * prior
    return new_belief