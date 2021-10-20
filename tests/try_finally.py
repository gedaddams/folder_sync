import try_finally2

try:
    try_finally2.testfunc()    
finally:
    print("after testfunc and after sys.exit was called!")