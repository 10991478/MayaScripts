def Add(numList):
    result = numList[0]

    for i in range(1,len(numList)):
        result += numList[i]
    
    return result

def Subtract(numList):
    result = numList[0]

    for i in range(1,len(numList)):
        result -= numList[i]
    
    return result

def Multiply(numList):
    result = numList[0]

    for i in range(1,len(numList)):
        result *= numList[i]
    
    return result

def Divide(numList):
    result = numList[0]

    for i in range(1,len(numList)):
        result /= numList[i]
    
    return result