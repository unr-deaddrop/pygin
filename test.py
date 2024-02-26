import abc

class A(abc.ABC):
    def x(self, **kwargs):
        return 1
    
class B(A):
    def x(self, a: str, b: str, **kwargs):
        return 1
    
