import random
rand_list = random.sample(range(1, 20), k=10)

list_comprehension_below_10 = [i for i in rand_list if i < 10]

list_comprehension_below_10 = list(filter(lambda x: x < 10, rand_list))