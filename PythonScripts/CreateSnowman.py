import maya.cmds as mc

def CreateSnowMan(ballSizes[], overLap):
    moveDist = 0
    currentObj = []
    middleBallSize = ballSizes[len(ballSizes)/2]
    #creating the snowballs
    for i in range(len(ballSizes)):
        if i == 0:
            moveDist = ballSizes[i]
        elif ballSizes[i] <= ballSizes[i - 1]:
            moveDist += ballSizes[i]*overLap
        elif ballSizes[i] > ballSizes[i - 1]:
            moveDist += ballSizes[i]
        currentObj = mc.polySphere("snowmanBall0", radius = ballSizes[i], subdivisionsX = 20, subdivisionsY = 20, axis = [0, 1, 0], createUVs = 2, constructionHistory = 1)
        if i == len(ballSizes)/2:
            middleBall = currentObj[0]
        mc.move(currentObj[0],, worldSpace, worldSpaceDistance 0 moveDist 0)
        if i == len(ballSizes) - 1:
            moveDist += 0
        elif (ballSizes[i] < ballSizes[i + 1]):
            moveDist += ballSizes[i]*overLap
        elif (ballSizes[i] >= ballSizes[i + 1]):
            moveDist += ballSizes[i]
        
    
    lastBallSize = ballSizes[len(ballSizes) - 1]
    #creating the nose
    currentObj = polyCone("snowmanNose", radius = (lastBallSize/4), height = (1.5*lastBallSize), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 0, axis = [0 1 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
    move(currentObj[0], worldSpace = true, worldSpaceDistance = 0, moveDist = (lastBallSize*1.3))
    rotate(currentObj[0], relative = true, worldSpace = true, forceOrderXYZ [90 0 0])
    #creating the eyes
    currentObj = polySphere("snowmanEye", radius (lastBallSize/7), subdivisionsX 20, subdivisionsY 20, axis 0 1 0, createUVs 2, constructionHistory 1)
    move(currentObj[0], worldSpace = true, worldSpaceDistance = [(-1*lastBallSize/3), (moveDist + lastBallSize/10), (lastBallSize*0.9)])
    currentObj = polySphere("snowmanEye", radius (lastBallSize/7), subdivisionsX 20, subdivisionsY 20, axis 0 1 0, createUVs 2, constructionHistory 1)
    move(currentObj[0], worldSpace = true, worldSpaceDistance = [(lastBallSize/3), (moveDist + lastBallSize/10), (lastBallSize*0.9)])
    
    #creating the hat
    currentObj = polyCylinder(radius lastBallSize, height (lastBallSize/8), subdivisionsX 20, subdivisionsY 1, subdivisionsZ 1, axis 0 1 0, roundCap 0, createUVs 3, constructionHistory = 1)
    move(currentObj[0], worldSpace = true, worldSpaceDistance = [0, (moveDist + lastBallSize*overLap), 0])
    currentObj = polyCylinder("hatTop", radius = (lastBallSize*0.7), height = (lastBallSize*1.25), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
    move(currentObj[0], worldSpace = true, worldSpaceDistance = [0, (moveDist + lastBallSize*overLap + (lastBallSize*1.25)/2), 0])
    #creating the arms
    armDist = getAttr(middleBall + ".translateY")
    j = -1
    while j <= 1:
        currentObj = polyCylinder("armCylinder0", radius = (middleBallSize/8), height = (middleBallSize*2), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
        move(currentObj[0], worldSpace = true, worldSpaceDistance = [(j*middleBallSize*1.2), (armDist + middleBallSize*0.3), 0])
        rotate(currentObj[0], relative = true, worldSpace = true, forceOrderXYZ = [0, 0, (j*-60)])
        currentObj = polyCylinder("handCylinder0", radius = (middleBallSize/12), height = (middleBallSize/3), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
        move(currentObj[0], worldSpace = true, worldSpaceDistance = [(j*middleBallSize*1.7), (armDist + middleBallSize*0.85), 0])
        rotate(currentObj[0], relative = true, worldSpace = true, forceOrderXYZ = [0, 0, (j*20)])
        j += 2
    
    #creating the coal buttons
    for i in range(-1,2):
        currentObj = polySphere("coalButton0", radius = (middleBallSize/8), subdivisionsX = 20, subdivisionsY = 20, axis = [0, 1, 0], createUVs = 2, constructionHistory = 1)
        move(currentObj[0], worldSpace = true, worldSpaceDistance = [0, (armDist + i*(middleBallSize/3)), (middleBallSize - abs(i*middleBallSize/18))])

CreateSnowMan([6,3,4,2], 1)