import os
import inspect

class SysMacroFunc:
    @staticmethod
    def FILE_LINE()->str:
        stack = inspect.stack()
        filename = os.path.basename(stack[0].filename)
        lineno = stack[1].lineno
        return "%s:%s - "%(filename,lineno)
    
