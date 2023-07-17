### INTERFACE ###
class SSD_Resource(object):
    
    def __init__(self, ppa, parent = None):
        self.ppa = ppa
        self.parent = parent
        if parent != None :
            self.geo = parent.geo
        self.components = []
        
    def get_components(self, depth = 0):
        if depth == 0:
            ret = self.components
        else :
            ret = []
            for component in self.components:
                ret += component.get_components(depth-1)
        return ret
            

class SSD(SSD_Resource):
    
    def __init__(self, nr_ch=8, nr_chip=2, nr_block=32, nr_page=1024, page_size=16384):
        super().__init__(0, None)
        self.create_dev(nr_ch, nr_chip, nr_block, nr_page, page_size)
        
    def create_dev(self, nr_ch, nr_chip, nr_block, nr_page, page_size):
        geo = geometry(nr_ch, nr_chip, nr_block, nr_page, page_size)
        self.geo = geo

        self.create_channels(geo)
        self.chips  = self.get_components(1)
        self.blocks = self.get_components(2)
        self.pages  = self.get_components(3)
        
        self.check_ppa_list()
    
    def create_channels(self, geo):
        self.chs = [Channel(self.ppa + i*geo.tot_page//geo.tot_ch, self) for i in range(geo.ch_per_ssd)]
        self.components = self.chs
        for component in self.components:
            component.create_chips(geo)
    
    def check_ppa_list(self):        
        # page validation
        temp = 0
        for p in self.pages:
            values = p.ppa
            if( temp > p.ppa) :
                print("invalid ppa : " + str(values))
            else :
                print("page validation : " + str(values), end="\r")
            temp = values
        print("page validation : OK           ")
        
        # all component validation
        for p in self.pages:
            id0 = get_id(self.geo, p.parent.parent.parent.ppa)
            id1 = get_id(self.geo, p.parent.parent.ppa)
            id2 = get_id(self.geo, p.parent.ppa)
            id3 = get_id(self.geo, p.ppa)
        
            if (id0[0] ==   id1[0] == id2[0] == id3[0] and  # channel check
                            id1[1] == id2[1] == id3[1] and  # chip check
                            id2[2] == id3[2]) :             # block check
                print("component hierachy : ", end = "")
                print(p.to_string(), end ="        \r")
            else :
                print("invalid component id : ")
        
            
        print("component hierachy : OK                         ")
    
    def info(self):
        buff = ""
        
        # capacity
        size = self.geo.capacity
        buff += "total " + str(size) + "Bytes\n"
        
        G = size//(1024**3)
        size -= G*(1024**3)
        M = size//(1024**2)
        size -= M*(1024**2)
        K = size//(1024**1)
        size -= K*(1024**1)
        buff += "(" + str(G) + "G " + str(M) + "M " + str(K) + "K " + str(size) + "Bytes)\n"
        
        # geometry
        buff += "total ch:"+str(self.geo.tot_ch)+"\n"
        buff += "total chip:"+str(self.geo.tot_chip)+"\n"
        buff += "total block:"+str(self.geo.tot_block)+"\n"
        buff += "total page:"+str(self.geo.tot_page)+"\n"
        
        return buff

class Channel(SSD_Resource):
    
    def __init__(self, ppa, parent):
        super().__init__(ppa, parent)
        
    def create_chips(self, geo):    
        self.chips = [Chip(self.ppa + i*geo.tot_page//geo.tot_chip, self) for i in range(geo.chip_per_ch)]
        self.components = self.chips
        for component in self.components:
            component.create_blocks(geo)

class Chip(SSD_Resource):
    
    def __init__(self, ppa, parent):
        super().__init__(ppa, parent)
        
    def create_blocks(self, geo):            
        self.blocks = [Block(self.ppa + i*geo.tot_page//geo.tot_block, self) for i in range(geo.block_per_chip)]
        self.components = self.blocks
        for component in self.components:
            component.create_pages(geo)

class Block(SSD_Resource):
    
    def __init__(self, ppa, parent):
        super().__init__(ppa, parent)
        self.pe_cycle = 0
        self.nr_free_page = self.geo.page_per_block
        
    def create_pages(self, geo):
        self.pages = [ Page(self.ppa + i, self) for i in range(geo.page_per_block)]
        self.components = self.pages
        
    def erase(self):
        self.pe_cycle += 1
        for page in self.pages:
            page.free = True

class Page(SSD_Resource):
    
    def __init__(self, ppa, parent):
        super().__init__(ppa, parent)
        self.components = None
        self.free = True
        
    def wrtie(self):
        if self.free == False:
            return "error(already charged)"
        self.free = False
        self.nr_free_page -= 1
        return "done"
        
    def to_string(self):        
        id = get_id(self.geo, self.ppa)
        return "ch" + str(id[0]) + " chip" + str(id[1]) + " block" + str(id[2]) + " page" + str(id[3])

class geometry(SSD_Resource):
    
    def __init__(self, ch, chip, block, page, page_size):
        self.ch_per_ssd     = ch
        self.chip_per_ch    = chip
        self.block_per_chip = block
        self.page_per_block = page
        self.page_size      = page_size  # Bytes
        self.calculate_total()
    
    def calculate_total(self):
        self.tot_ch     = self.ch_per_ssd
        self.tot_chip   = self.chip_per_ch      * self.tot_ch 
        self.tot_block  = self.block_per_chip   * self.tot_chip
        self.tot_page   = self.page_per_block   * self.tot_block
        self.capacity   = self.page_size        * self.tot_page

def get_ppa(geo, ch = 0, chip = 0, block = 0, page = 0):
    ch_margin    = ch * geo.tot_page//geo.tot_ch
    chip_margin  = chip * geo.tot_page//geo.tot_chip
    block_margin = block * geo.tot_page//geo.tot_block
    page_offset  = page
    ppa = ch_margin + chip_margin + block_margin + page_offset
    return ppa

def get_id(geo, ppa):
    ch      = (ppa // (geo.tot_page//geo.tot_ch))       % geo.ch_per_ssd
    chip    = (ppa // (geo.tot_page//geo.tot_chip))     % geo.chip_per_ch
    block   = (ppa // (geo.tot_page//geo.tot_block))    % geo.block_per_chip
    page    = (ppa // (geo.tot_page//geo.tot_page))     % geo.page_per_block
    return [ch, chip, block, page]

