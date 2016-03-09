def my_func():
  print('called')

alias = my_func
my_list = [1, None, alias]
inception = my_list[2]

inception()
