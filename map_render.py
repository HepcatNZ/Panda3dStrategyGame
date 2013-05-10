from direct.showbase import DirectObject
from direct.showbase.ShowBase import ShowBase
from pandac.PandaModules import *
from direct.interval.IntervalGlobal import Sequence
from direct.task import Task

from direct.showbase.DirectObject import DirectObject
from pandac.PandaModules import CollisionHandlerEvent, CollisionNode, CollisionSphere, CollisionTraverser, BitMask32, CollisionRay
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage



import xml.etree.ElementTree as xml
#import ImageOps
import Image

import string

class StrategyGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.camera_control()



        self.REGION_MAP = "maps/italy_provs.png"
        self.TEXTURE_MAP = "maps/italy_terrain2.png"
        self.WORLD_MAP = "maps/italy_map.xml"
        self.SCENARIO_MAP = "scenarios/italy_scen.xml"

        self.terrainScale = 1 # Currently Broken

        self.keyboard_setup()

        self.drawTerrain()



        self.xml_load_map(self.WORLD_MAP,"WorldMap")
        self.xml_load_map(self.SCENARIO_MAP,"Scenario")
        self.init_collisions()
        self.pickingEnabledObject = None

        self.taskMgr.add(self.camera_update, "UpdateCameraTask")

        self.generate_models()
        self.txtBox = OnscreenText("<No province>")
        self.setup_collision_calcs()
        taskMgr.add(self.rayUpdate, "updatePicker")
        taskMgr.doMethodLater(0.2,self.task_calendar, "calendar")
        self.init_variables()
        self.interface()

    def init_variables(self):
        self.armies = [[],[]]
        for n in range(len(self.nations)):
            self.armies.append(n)
        self.target = 0
        self.army_count = 0
        self.selected_prov = -1
        self.months = ["January","February","March","April","May","June",
                       "July","August","September","October","November","December"]
        self.adce = "AD"
        self.player = 1
        self.money_inc = 0
        for p in range(len(self.provs)):
            if self.provs_owner[p] == self.player:
                self.money_inc += self.provs_money[p]
        self.men_inc = 0
        for p in range(len(self.provs)):
            if self.provs_owner[p] == self.player:
                self.men_inc += self.provs_men[p]

    def draw_card(self,x,y,width,height,colour):

        cm = CardMaker("CardMaker")
        cm.setFrame(x, x+width,y+height, y)
        card = render2d.attachNewNode(cm.generate())
        card.setColor(colour)
        return (card)

    def interface(self):
        self.interface_back = self.draw_card(-0.8,-1,1.6,0.4,(100,100,100,100))

        self.txt_name = OnscreenText(text = "", pos = (-0.8,-0.7,-0.8))
        self.txt_money = OnscreenText(text = "", pos = (-0.8,-0.8,-0.8))
        self.txt_men = OnscreenText(text = "", pos = (-0.8,-0.9,-0.8))
        self.txt_nation = OnscreenText(text = self.nations[self.player-1], pos = (-1.2,0.9,-0.8))
        self.txt_nation_money = OnscreenText(text = "Coin: " + str(self.nations_money[self.player-1])+" +"+str(self.money_inc), pos = (-0.4,0.9,-0.8))
        self.txt_nation_men = OnscreenText(text = "Manpower: " + str(self.nations_men[self.player-1])+" +"+str(self.men_inc), pos = (0.4,0.9,-0.8))
        self.txt_date = OnscreenText(text = str(self.day)+" of "+self.months[self.month-1]+" "+str(self.year)+self.adce, pos = (-1.0,0.8,-0.8))

    def task_calendar(self,task):
        #task.delayTime = 5
        if (self.month == 1 or self.month == 3 or self.month == 5 or
            self.month == 7 or self.month == 8 or self.month == 10 or self.month == 12):
                if self.day == 31 and self.month == 12:
                    self.day = 1
                    self.month = 1
                    self.year += 1
                elif self.day == 31:
                    self.day = 1
                    self.month += 1
                else:
                    self.day += 1
        elif (self.month == 4 or self.month == 6 or self.month == 9 or self.month == 11):
            if self.day == 30:
                self.day = 1
                self.month += 1
            else:
                self.day += 1
        elif (self.month == 2):
#            if isleap:
#                print self.year/4
#                print "LEAP YEAR"
#                if self.day == 29:
#                    self.day = 1
#                    self.month = 3
#                else:
#                    self.day += 1
#            else:
            print "IS NOT A LEAP YEAR"
            if self.day == 28:
                self.day = 1
                self.month = 3
            else:
                self.day += 1
        self.daypass()
        return Task.again

    def daypass(self):
        self.nations_money[self.player-1] += self.money_inc
        self.nations_men[self.player-1] += self.men_inc
        self.update_interface()

    def update_interface(self):
        self.txt_date.setText(str(self.day)+" of "+self.months[self.month-1]+" "+str(self.year)+self.adce)
        self.txt_nation_money.setText("Coin: " + str(self.nations_money[self.player-1])+" +"+str(self.money_inc))
        self.txt_nation_men.setText("Manpower: " + str(self.nations_men[self.player-1])+" +"+str(self.men_inc))
        if self.selected_prov != -1:
            self.txt_name.setText("Province: "+self.provs[self.selected_prov])
            self.txt_money.setText("Income: "+str(self.provs_money[self.selected_prov]))
            self.txt_men.setText("Manpower: "+str(self.provs_men[self.selected_prov]))
            self.interface_back.setColor(self.format_colour_tuple(self.nations_rgb[self.provs_owner[self.selected_prov]-1]))
        else:
            self.txt_name.setText("")
            self.txt_money.setText("")
            self.txt_men.setText("")
            self.interface_back.setColor((255,255,255,255))

    def army_create(self):
        id = self.army_count+1
        army = self.loader.loadModel("models/man.x")
        self.armies[0].append(id)
        army.reparentTo(self.render)
        army.setName(str(id))
        army.setScale(1, 1, 1)
        x = 50
        y = 50
        target = self.target
        target_x = float(self.provs_x[target])
        target_y = 257-float(self.provs_y[target])
        target_z = float(self.getObjectZ(target_x,target_y)-1)
        oArmyCol = army.attachNewNode(CollisionNode("BuildingCNode%d"%id))
        oArmyCol.setScale((2,2,2))
        oArmyCol.node().addSolid(CollisionSphere(0,0,0,1))
        oArmyCol.setTag("unit","army")
        oArmyCol.show()
        point1 = Point3(x,y,0)
        point2 = Point3(target_x,target_y,target_z)
        distance = (point1.getXy() - point2.getXy()).length()
        myInterval = army.posInterval(distance/10, Point3(target_x,target_y, target_z))
        mySequence = Sequence(myInterval)
        mySequence.start()
        army.setPos(x, y, self.getObjectZ(x,y)-1)
        army.setTag("target",str(target))
        self.army_count += 1
        if (self.target<len(self.provs)-1):
            self.target += 1
        else:
            self.target = 0
        #taskMgr.add()

    def army_update(self,id):
        point1 = self.armies[0][id-1].getPos()
        point2 = Point3(target_x,target_y,target_z)
        distance = (point1.getXy() - point2.getXy()).length()

    def init_collisions(self):
        base.cTrav = CollisionTraverser()
        self.cHandler = CollisionHandlerEvent()

        pickerNode = CollisionNode("mouseRayNode")
        pickerNPos = base.camera.attachNewNode(pickerNode)
        self.pickerRay = CollisionRay()
        pickerNode.addSolid(self.pickerRay)

        pickerNode.setTag("rays","ray1")
        base.cTrav.addCollider(pickerNPos, self.cHandler)

    def setup_collision_calcs(self):
        self.cHandler.addInPattern("%(rays)ft-into-%(prov)it")
        self.cHandler.addOutPattern("%(rays)ft-out-%(prov)it")

        self.cHandler.addAgainPattern("ray_again_all%(""rays"")fh%(""prov"")ih")

        self.DO=DirectObject()

        self.DO.accept('ray1-into-city', self.collideInBuilding)
        self.DO.accept('ray1-out-city', self.collideOutBuilding)

        self.DO.accept('ray_again_all', self.collideAgainstBuilds)

        self.pickingEnabledOject=None

        self.DO.accept('mouse1', self.mouseClick, ["down"])
        self.DO.accept('mouse1-up', self.mouseClick, ["up"])

    def camera_control(self):
        base.disableMouse()

        self.camera = base.camera

        self.cam_speed = 3
        self.cam_drag = 0.01

        self.cam_x_moving = False
        self.cam_y_moving = False
        self.cam_z_moving = False

        self.cam_x_inc = 0
        self.cam_y_inc = 0
        self.cam_z_inc = 0

        self.cameraDistance = -50
        self.camHeight = 25


        self.camXAngle = 0
        self.camYAngle = -25
        self.camZAngle = 0

        self.camX = 0
        self.camY = 0
        self.camZ = 100

    def camera_update(self,task):

        if self.cam_x_moving:
            self.camX+=self.cam_x_inc
        elif self.cam_x_inc != 0:
            if (self.cam_x_inc > 0 and self.cam_x_inc-self.cam_drag <= 0) or (self.cam_x_inc < 0 and self.cam_x_inc+self.cam_drag >= 0):
                self.cam_x_inc = 0
            elif self.cam_x_inc > 0:
                self.cam_x_inc -= self.cam_drag
            elif self.cam_x_inc < 0:
                self.cam_x_inc -= self.cam_drag
            else:
                print "FUCKUP WITH CAM X INC"

        if self.cam_y_moving:
            self.camY+=self.cam_y_inc
        elif self.cam_y_inc != 0:
            if (self.cam_y_inc > 0 and self.cam_y_inc-self.cam_drag <= 0) or (self.cam_y_inc < 0 and self.cam_y_inc+self.cam_drag >= 0):
                self.cam_y_inc = 0
            elif self.cam_y_inc > 0:
                self.cam_y_inc -= self.cam_drag
            elif self.cam_y_inc < 0:
                self.cam_y_inc -= self.cam_drag
            else:
                print "FUCKUP WITH CAM Y INC"

        if self.cam_z_moving:
            self.camZ+=self.cam_z_inc
        elif self.cam_z_inc != 0:
            if (self.cam_z_inc > 0 and self.cam_z_inc-self.cam_drag <= 0) or (self.cam_z_inc < 0 and self.cam_z_inc+self.cam_drag >= 0):
                self.cam_z_inc = 0
            elif self.cam_z_inc > 0:
                self.cam_z_inc -= self.cam_drag
            elif self.cam_z_inc < 0:
                self.cam_z_inc -= self.cam_drag
            else:
                print "FUCKUP WITH CAM Z INC"

        self.camera.setPos(self.camX, self.camY, self.camZ)
        self.camera.setHpr(self.camXAngle, self.camYAngle, self.camZAngle)

        return Task.cont

    def camera_move(self, status):
        if status == "up":
            self.cam_y_moving = True
            self.cam_y_inc = self.cam_speed
        if status == "down":
            self.cam_y_moving = True
            self.cam_y_inc = -self.cam_speed
        if status == "left":
            self.cam_x_moving = True
            self.cam_x_inc = -self.cam_speed
        if status == "right":
            self.cam_x_moving = True
            self.cam_x_inc = self.cam_speed
        if status == "stopX":
            self.cam_x_moving = False
        if status == "stopY":
            self.cam_y_moving = False

    def keyboard_setup(self):
        self.accept("w", self.keyW)
        self.accept("w-up", self.stop_y)
        self.accept("s", self.keyS)
        self.accept("s-up", self.stop_y)
        self.accept("a", self.keyA)

        self.accept("a-up", self.stop_x)
        self.accept("d", self.keyD)
        self.accept("d-up", self.stop_x)
        self.accept("+", self.ZoomIn)
        self.accept("c", self.createArmy)

    def createArmy(self):
        self.army_create()

    def ZoomIn(self):
        self.camZ -= 1

    def keyW( self ):
        self.camera_move("up")

    def keyS( self ):
        self.camera_move("down")

    def keyA( self ):
        self.camera_move("left")

    def keyD( self ):
        self.camera_move("right")

    def stop_x( self ):
        self.camera_move("stopX")

    def stop_y( self ):
        self.camera_move("stopY")

    def generate_models(self):
        for p in range(len(self.provs)):
            print "Making",self.provs[p]
            city = self.loader.loadModel("models/house2.x")
            city.reparentTo(self.render)
            city.setName(self.provs[p])
            city.setScale(2, 2, 2)
            x = float(self.provs_x[p]*self.terrainScale)
            y = 257*self.terrainScale-float(self.provs_y[p]*self.terrainScale)
            city.setPos(x, y, self.getObjectZ(x,y)-1)
            oCityCol = city.attachNewNode(CollisionNode("BuildingCNode%d"%p))
            oCityCol.setScale((3,3,3))
            oCityCol.node().addSolid(CollisionSphere(0,0,0,1))
            oCityCol.setTag("prov","city")
            city.setTag("id",str(p+1))
            #oCityCol.show()

    def collideInBuilding(self,entry):
        np_into=entry.getIntoNodePath()
        np_into.getParent().setColor(.6,.5,1.0,1)

    def collideOutBuilding(self,entry):

        np_into=entry.getIntoNodePath()
        np_into.getParent().setColor(1.0,1.0,1.0,1)

        self.pickingEnabledObject = None
        self.txtBox.setText("<No province>")

    def collideAgainstBuilds(self,entry):
        if entry.getIntoNodePath().getParent() <> self.pickingEnabledOject:
            np_from=entry.getFromNodePath()
            np_into=entry.getIntoNodePath()

            self.pickingEnabledObject = np_into.getParent()


            self.txtBox.setText(self.pickingEnabledObject.getName())

    def mouseClick(self,status):
        if self.pickingEnabledObject:
            if status == "down":
                self.pickingEnabledObject.setScale(0.95*2)
                print self.pickingEnabledObject.getTag("id"),self.provs[int(self.pickingEnabledObject.getTag("id"))-1]
                self.selected_prov = int(self.pickingEnabledObject.getTag("id"))-1
                self.update_interface()

            if status == "up":
                self.pickingEnabledObject.setScale(1.0*2)
        elif self.pickingEnabledObject == None:
            self.selected_prov = -1
            self.update_interface()

    def rayUpdate(self,task):
        if base.mouseWatcherNode.hasMouse():
            mpos = base.mouseWatcherNode.getMouse()

            self.pickerRay.setFromLens(base.camNode, mpos.getX(),mpos.getY())
        return task.cont

    def getObjectZ(self, x, y):
        if ((x > 0) and (x < 257) and (y > 0) and (y < 257)):
            return(self.terrain.getElevation(x,y)*self.terrainSize)
        else:
            return 0
    def format_colour_tuple(self,colour):
        col = string.split(colour)
        tuple = (int(col[0]),int(col[1]),int(col[2]),255)
        return tuple


    def drawTerrain(self):
        self.terrainSize = 5
        heightmap = "maps/italy_heightmap.png"
        colmap = self.TEXTURE_MAP



        self.terrain = GeoMipTerrain("terrain")
        self.terrain.setHeightfield(heightmap)
        self.terrain.setColorMap(colmap)

        self.terrain.setBlockSize(64)
        #self.terrain.setNear(40)
        #self.terrain.setFar(120)
        #self.terrain.setMinLevel(1)
        self.terrain.setBruteforce(True)

        self.terrain.generate()
        self.terrain.setAutoFlatten(self.terrain.AFMLight)

        self.root = self.terrain.getRoot()
        self.root.reparentTo(render)
        self.root.setSz(self.terrainSize)
        #self.root.setScale(self.terrainScale,self.terrainScale,1)



    def xml_load_map(self,file,type):
        if type == "WorldMap":
            tree = xml.parse(file)
            root = tree.getroot()

            self.provs = []
            self.provs_x = []
            self.provs_y = []
            self.provs_rgb = []
            self.provs_owner = []
            self.provs_money = []
            self.provs_men = []

            counter = 1
            for p in root.findall("province"):
                self.provs.append(self.get_tag(root,"province", counter, "name"))
                self.provs_x.append(self.get_tag(root, "province", counter, "x"))
                self.provs_y.append(self.get_tag(root, "province", counter, "y"))
                self.provs_rgb.append(self.get_tag(root, "province", counter, "rgb"))
                self.provs_owner.append(0)
                self.provs_money.append(0)
                self.provs_men.append(0)
                counter+=1
        elif type == "Scenario":
            tree = xml.parse(file)
            root = tree.getroot()
            self.day = 0
            self.month = 0
            self.year = 0
            self.adce = 0

            self.day = int(root.attrib["day"])
            self.month = int(root.attrib["month"])
            self.year = int(root.attrib["year"])

            self.nations = []
            self.nations_rgb = []
            self.nations_capital = []
            self.nations_money = []
            self.nations_men = []
            self.nations_provs_id = []

            counter = 0
            for p in root.findall("province"):
                print p.attrib["id"]

            for n in root.findall("nation"):
                for p in n.findall("province"):
                    self.provs_owner[int(p.attrib["id"])-1] = int(p.find("owner").text)
                    self.provs_money[int(p.attrib["id"])-1] = int(p.find("money").text)
                    self.provs_men[int(p.attrib["id"])-1] = int(p.find("men").text)
                    print self.provs_owner[int(p.attrib["id"])-1]
                    counter+=1
            counter = 1
            for n in root.findall("nation"):
                self.nations.append(self.get_tag(root, "nation", counter, "name"))
                self.nations_capital.append(n.attrib["capital"])
                #print self.nations_capital
                self.nations_rgb.append(self.get_tag(root, "nation", counter, "rgb"))
                self.nations_money.append(int(self.get_tag(root, "nation", counter, "money")))
                self.nations_men.append(int(self.get_tag(root, "nation", counter, "men")))
                counter += 1

    def get_tag(self,root,str_tag,prov_id, prov_tag):
        prov = root.find('.//'+str_tag+'[@id="'+str(prov_id)+'"]')
        tag = prov.find(prov_tag).text
        return tag

app = StrategyGame()
app.setFrameRateMeter(True)
app.run()