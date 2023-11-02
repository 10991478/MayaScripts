import maya.cmds as cmds

def CreateSnowMan(ballSizes, overLap):
    moveDist = 0
    currentObj = []
    middleBallSize = ballSizes[(int)(len(ballSizes)/2)]
    #creating the snowballs
    for i in range(0, len(ballSizes)):
        if i == 0:
            moveDist = ballSizes[i]
        elif ballSizes[i] <= ballSizes[i - 1]:
            moveDist += ballSizes[i]*overLap
        elif ballSizes[i] > ballSizes[i - 1]:
            moveDist += ballSizes[i]
        currentObj = cmds.polySphere(name = "snowmanBall0", radius = ballSizes[i], subdivisionsX = 20, subdivisionsY = 20, axis = [0, 1, 0], createUVs = 2, constructionHistory = 1)
        if i == len(ballSizes)/2:
            middleBall = currentObj[0]
        cmds.move(0, moveDist, 0, currentObj[0], worldSpace = True, worldSpaceDistance = True)
        if i == len(ballSizes) - 1:
            moveDist += 0
        elif ballSizes[i] < ballSizes[i + 1]:
            moveDist += ballSizes[i]*overLap
        elif ballSizes[i] >= ballSizes[i + 1]:
            moveDist += ballSizes[i]
    lastBallSize = ballSizes[len(ballSizes) - 1]


    #creating the nose
    currentObj = cmds.polyCone(name = "snowmanNose", radius = (lastBallSize/4), height = (1.5*lastBallSize), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 0, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
    cmds.move(0, moveDist, (lastBallSize*1.3), currentObj[0], worldSpace = True, worldSpaceDistance = True)
    cmds.rotate(90, 0, 0, currentObj[0], relative = True, worldSpace = True, forceOrderXYZ = True)

    #creating the eyes
    currentObj = cmds.polySphere(name = "snowmanEye", radius = (lastBallSize/7), subdivisionsX = 20, subdivisionsY = 20, axis = [0, 1, 0], createUVs = 2, constructionHistory = 1)
    cmds.move((-1*lastBallSize/3), (moveDist + lastBallSize/10), (lastBallSize*0.9), currentObj[0], worldSpace = True, worldSpaceDistance = True)
    currentObj = cmds.polySphere(name = "snowmanEye", radius = (lastBallSize/7), subdivisionsX = 20, subdivisionsY = 20, axis = [0, 1, 0], createUVs = 2, constructionHistory = 1)
    cmds.move((lastBallSize/3), (moveDist + lastBallSize/10), (lastBallSize*0.9), currentObj[0], worldSpace = True, worldSpaceDistance = True)
    
    #creating the hat
    currentObj = cmds.polyCylinder(radius = lastBallSize, height = (lastBallSize/8), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
    cmds.move(0, (moveDist + lastBallSize*overLap), 0, currentObj[0], worldSpace = True, worldSpaceDistance = True)
    currentObj = cmds.polyCylinder(name = "hatTop", radius = (lastBallSize*0.7), height = (lastBallSize*1.25), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
    cmds.move(0, (moveDist + lastBallSize*overLap + (lastBallSize*1.25)/2), 0, currentObj[0], worldSpace = True, worldSpaceDistance = True)

    #creating the arms
    armDist = cmds.getAttr(middleBall + ".translateY")
    for i in range(-1,2,2):
        currentObj = cmds.polyCylinder(name = "armCylinder0", radius = (middleBallSize/8), height = (middleBallSize*2), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
        cmds.move((i*middleBallSize*1.2), (armDist + middleBallSize*0.3), 0, currentObj[0], worldSpace = True, worldSpaceDistance = True)
        cmds.rotate(0, 0, (i*-60), currentObj[0], relative = True, worldSpace = True, forceOrderXYZ = True)
        currentObj = cmds.polyCylinder(name = "handCylinder0", radius = (middleBallSize/12), height = (middleBallSize/3), subdivisionsX = 20, subdivisionsY = 1, subdivisionsZ = 1, axis = [0, 1, 0], roundCap = 0, createUVs = 3, constructionHistory = 1)
        cmds.move((i*middleBallSize*1.7), (armDist + middleBallSize*0.85), 0, currentObj[0], worldSpace = True, worldSpaceDistance = True)
        cmds.rotate(0, 0, (i*20), currentObj[0], relative = True, worldSpace = True, forceOrderXYZ = True)
    
    #creating the coal buttons
    for i in range(-1,2):
        currentObj = cmds.polySphere(name = "coalButton0", radius = (middleBallSize/8), subdivisionsX = 20, subdivisionsY = 20, axis = [0, 1, 0], createUVs = 2, constructionHistory = 1)
        cmds.move(0, (armDist + i*(middleBallSize/3)), (middleBallSize - abs(i*middleBallSize/18)), currentObj[0], worldSpace = True, worldSpaceDistance = True)

CreateSnowMan([6,3,4,2], 1)