from rlutilities .simulation import Input 




class Jump :
    def __init__ (self ,duration ):

        self .duration =duration 
        self .controls =Input ()

        self .timer =0 
        self .counter =0 

        self .finished =False 

    def interruptible (self )->bool :
        return False 

    def step (self ,dt ):

        self .controls .jump =self .timer <self .duration 

        if not self .controls .jump :
            self .counter +=1 

        self .timer +=dt 

        if self .counter >=2 :
            self .finished =True 

        return self .finished 
