package expedition.industry;

import com.google.gson.JsonParser;
import com.lowdragmc.mbd2.api.blockentity.ProxyPartBlockEntity;
import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.simibubi.create.content.logistics.box.PackageItem;
import com.simibubi.create.content.logistics.packagerLink.LogisticallyLinkedBehaviour;
import com.simibubi.create.content.logistics.packagerLink.PackagerLinkBlockEntity;
import com.simibubi.create.content.logistics.stockTicker.PackageOrderWithCrafts;
import de.theidler.create_mobile_packages.CMPHelper;
import de.theidler.create_mobile_packages.blocks.bee_port.BeePortBlockEntity;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.IFluidHandler.FluidAction;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.items.ItemHandlerHelper;
import org.apache.commons.lang3.mutable.MutableBoolean;

public final class WorksitesAcceptance {
    private static final String NS = "expedition_industry:";
    private static final String RECEIVE = "worksites-proof-in";
    private static final String REMOTE = "worksites-proof-remote";
    private static final String SEND = "worksites-proof-out";
    private static final BlockPos BEACON = new BlockPos(462, 164, 374);
    private record Site(String name, BlockPos anchor, BlockPos origin, Rotation rotation) {
        BlockPos at(int x,int y,int z) {
            return anchor.offset(new BlockPos(x,y,z).subtract(origin).rotate(rotation));
        }
        Direction face(Direction face) { return rotation.rotate(face); }
    }
    private final Site furnace = new Site("shaft_furnace",new BlockPos(420,162,352),
        new BlockPos(3,2,1),Rotation.NONE);
    private final Site cell = new Site("electrolytic_cell",new BlockPos(452,162,352),
        new BlockPos(3,2,1),Rotation.CLOCKWISE_90);
    private final Site shop = new Site("trading_station",new BlockPos(440,162,374),
        new BlockPos(4,2,1),Rotation.NONE);
    private final List<Site> sites = List.of(furnace,cell,shop);
    private long started = -1;
    private int industrialStep, dispatchStep;

    public WorksitesAcceptance() {
        NeoForge.EVENT_BUS.addListener((RegisterCommandsEvent event) -> event.getDispatcher().register(
            Commands.literal("expeditionworksitesproof").requires(source -> source.hasPermission(4)).executes(context -> {
                try {
                    begin(context.getSource().getServer().overworld());
                } catch (Exception error) {
                    throw new IllegalStateException("worksite fixtures",error);
                }
                return 1;
            })));
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void begin(ServerLevel level) throws Exception {
        var layout=JsonParser.parseString(Files.readString(Path.of("brass-fixtures.json"))).getAsJsonObject();
        for (var site : sites) {
            for (int x=-1;x<=1;x++) for (int z=-1;z<=1;z++)
                level.setChunkForced((site.anchor().getX()>>4)+x,(site.anchor().getZ()>>4)+z,true);
            level.removeBlock(site.anchor(),false);
            for (var raw : layout.getAsJsonArray(site.name())) {
                var entry=raw.getAsJsonArray();
                String block=entry.get(3).getAsString();
                if (block.equals(NS+site.name())) continue;
                var pos=site.at(entry.get(0).getAsInt(),entry.get(1).getAsInt(),entry.get(2).getAsInt());
                level.setBlock(pos,state(level,block).rotate(site.rotation()),Block.UPDATE_CLIENTS);
            }
            level.setBlockAndUpdate(site.anchor(),state(level,NS+site.name()+"[facing=north]").rotate(site.rotation()));
        }
        level.setChunkForced(BEACON.getX()>>4,BEACON.getZ()>>4,true);
        level.removeBlock(BEACON,false);
        level.setBlockAndUpdate(BEACON,state(level,"create_mobile_packages:bee_port[facing=north]"));
        // The test fixture establishes native redstone and hopper neighbor states.
        level.updateNeighborsAt(shop.at(1,4,4),level.getBlockState(shop.at(1,4,4)).getBlock());
        industrialStep=dispatchStep=0;
        started=level.getGameTime();
    }

    private void tick(ServerTickEvent.Post event) {
        if (started<0) return;
        var level=event.getServer().overworld();
        long time=level.getGameTime()-started;
        try {
            if(time>=100 && industrialStep==0){
                for(var site:sites)require(machine(level,site).isFormedValid(),"structure "+site.name()+" at "
                    +machine(level,site).getMultiblockState().getPos());
                power(level,furnace,5,2,6);power(level,cell,5,2,5);power(level,shop,7,2,5);
                inject(level,furnace,2,9,3,Direction.WEST,new ItemStack(Items.COAL,4));
                fill(level,furnace,0,3,5,Direction.WEST,"mekanism:oxygen",200);
                fill(level,furnace,6,4,5,Direction.EAST,"cmi:molten_industrial_iron",360);
                fill(level,cell,3,2,6,Direction.SOUTH,"minecraft:water",1000);
                require(level.getCapability(Capabilities.FluidHandler.BLOCK,cell.anchor(),Direction.NORTH)==null,
                    "the console must not attach to a pipe");
                beginFlights(level);
                industrialStep=1;
                System.out.println("EXPEDITION_WORKSITES_FORM_PORTS_PASS");
            }
            if(time>=315 && industrialStep==1){
                var output=items(level,furnace,2,1,0,Direction.NORTH);
                var bloom=output.extractItem(0,64,false);
                require(bloom.is(item(NS+"semi_finished_steel")) && bloom.getCount()==4,"steel bloom "+bloom);
                inject(level,furnace,2,9,3,Direction.WEST,bloom);
                inject(level,furnace,2,9,3,Direction.WEST,new ItemStack(item(NS+"aluminum_slag")));
                drain(level,cell,0,3,4,Direction.WEST,"mekanism:hydrogen",666);
                drain(level,cell,6,3,4,Direction.EAST,"mekanism:oxygen",333);
                industrialStep=2;
                System.out.println("EXPEDITION_WORKSITES_BLOOM_AND_GASES_PASS");
            }
            if(time>=500 && industrialStep==2){
                drain(level,furnace,3,1,7,Direction.SOUTH,"modernfoundry:molten_steel",360);
                industrialStep=3;
                System.out.println("EXPEDITION_WORKSITES_STEEL_PASS");
            }
            if(industrialStep>0)tickFlights(level);
            if(industrialStep==3 && dispatchStep==2){
                require(machine(level,shop).isFormedValid(),"bee traffic must preserve the shop shape");
                level.setBlockAndUpdate(shop.at(2,5,4),Blocks.COBBLESTONE.defaultBlockState());
                dispatchStep=3;
            }
            if(dispatchStep==3 && !machine(level,shop).isFormedValid()){
                require(level.getBlockEntity(shop.at(2,4,4)) instanceof BeePortBlockEntity,"native bee port persists");
                level.removeBlock(shop.at(2,5,4),false);
                dispatchStep=4;
            }
            if(dispatchStep==4 && machine(level,shop).isFormedValid()){
                System.out.println("EXPEDITION_WORKSITES_COMPLETE");
                started=-1;
            }
            require(time<1350,"shop cargo timeout at stage "+dispatchStep);
        } catch(Exception error){
            System.out.println("EXPEDITION_WORKSITES_FAIL "+error);
            error.printStackTrace(System.out);
            started=-1;
        }
    }

    private void beginFlights(ServerLevel level) {
        var remote=(BeePortBlockEntity)level.getBlockEntity(BEACON);
        var in=bee(level,shop,2,4,4);
        var out=bee(level,shop,6,3,4);
        require(level.hasNeighborSignal(in.getBlockPos())&&!level.hasNeighborSignal(out.getBlockPos()),"independent redstone modes");
        require(!level.hasNeighborSignal(shop.at(2,3,4)),"receive lever cannot trigger unpacker's redstone");
        var group=UUID.randomUUID();
        for(var port:List.of(in,out,remote)){
            port.behaviour.freqId=group;
            LogisticallyLinkedBehaviour.keepAlive(port.behaviour);
            port.setBeeReturnModeEnabled(false);
        }
        address(in,RECEIVE,true);
        address(out,SEND,false);
        address(remote,REMOTE,true);
        var stock=(PackagerLinkBlockEntity)level.getBlockEntity(shop.at(7,2,4));
        require(stock.getPackager()!=null && stock.getPackager().getBlockPos().equals(shop.at(6,2,4)),"native stock link mount");
        stock.behaviour.freqId=group;
        LogisticallyLinkedBehaviour.keepAlive(stock.behaviour);
        require(CMPHelper.getClosestBeePort(level,RECEIVE,BEACON,null,group)==in,"native address routing");
        remote.addBeeToRoboBeeInventory(1);
        out.addBeeToRoboBeeInventory(1);
        var packageStack=PackageItem.containing(List.of(new ItemStack(Items.COPPER_BLOCK)));
        PackageItem.addAddress(packageStack,RECEIVE);
        require(remote.addItemStack(packageStack,false),"native package queue");
    }

    private void tickFlights(ServerLevel level) {
        var credit=item(NS+"trade_credit");
        if(dispatchStep==0 && count(items(level,shop,6,1,4,Direction.SOUTH),credit)>=2){
            var stock=(PackagerLinkBlockEntity)level.getBlockEntity(shop.at(7,2,4));
            var request=stock.processRequest(new ItemStack(credit),2,REMOTE,0,new MutableBoolean(true),1217,
                PackageOrderWithCrafts.empty(),null);
            require(request!=null,"native packager must reserve credits from vault");
            request.getFirst().attemptToSend(new ArrayList<>(List.of(request.getSecond())));
            dispatchStep=1;
            System.out.println("EXPEDITION_WORKSITES_RECEIVE_UNPACK_AND_SETTLE_PASS");
        }
        if(dispatchStep==1){
            var remote=(BeePortBlockEntity)level.getBlockEntity(BEACON);
            for(int slot=0;slot<remote.inventory.getSlots();slot++){
                var delivery=remote.inventory.getStackInSlot(slot);
                if(PackageItem.isPackage(delivery) && PackageItem.getAddress(delivery).equals(REMOTE)
                        && count(PackageItem.getContents(delivery),credit)==2){
                    dispatchStep=2;
                    System.out.println("EXPEDITION_WORKSITES_PACK_AND_FLY_PASS");
                    return;
                }
            }
        }
    }

    private static void address(BeePortBlockEntity port,String address,boolean accepts){
        port.addressFilter=address;
        port.acceptsPackages=accepts;
        port.filterChanged();
    }

    private static BeePortBlockEntity bee(ServerLevel level,Site site,int x,int y,int z){
        return (BeePortBlockEntity)level.getBlockEntity(site.at(x,y,z));
    }
    private static int count(IItemHandler handler,Item item){
        int count=0;
        if(handler==null)return 0;
        for(int slot=0;slot<handler.getSlots();slot++){
            var stack=handler.getStackInSlot(slot);
            if(stack.is(item))count+=stack.getCount();
        }
        return count;
    }
    private static IItemHandler items(ServerLevel level,Site site,int x,int y,int z,Direction face){
        return level.getCapability(Capabilities.ItemHandler.BLOCK,site.at(x,y,z),site.face(face));
    }
    private static void inject(ServerLevel level,Site site,int x,int y,int z,Direction face,ItemStack item){
        var capability=items(level,site,x,y,z,face);
        require(capability!=null && ItemHandlerHelper.insertItemStacked(capability,item,false).isEmpty(),"insert "+item);
    }
    private static FluidStack fluid(String name,int amount){
        return new FluidStack(BuiltInRegistries.FLUID.get(ResourceLocation.parse(name)),amount);
    }
    private static void fill(ServerLevel level,Site site,int x,int y,int z,Direction face,String name,int amount){
        var port=level.getCapability(Capabilities.FluidHandler.BLOCK,site.at(x,y,z),site.face(face));
        require(port!=null && port.fill(fluid(name,amount),FluidAction.EXECUTE)==amount,"fill "+name);
    }
    private static void drain(ServerLevel level,Site site,int x,int y,int z,Direction face,String name,int amount){
        var port=level.getCapability(Capabilities.FluidHandler.BLOCK,site.at(x,y,z),site.face(face));
        require(port!=null && port.drain(fluid(name,amount),FluidAction.EXECUTE).getAmount()==amount,"drain "+name);
    }
    private static void power(ServerLevel level,Site site,int x,int y,int z){
        var pos=site.at(x,y,z);
        require(level.getBlockEntity(pos) instanceof ProxyPartBlockEntity proxy && proxy.getOriginalState()!=null,
            "real formed relay "+site.name());
        var receiver=level.getCapability(Capabilities.EnergyStorage.BLOCK,pos,site.face(Direction.EAST));
        require(receiver!=null && !receiver.canExtract(),"one-way FE port "+site.name());
        for(int i=0;i<10;i++)require(receiver.receiveEnergy(8000,false)==8000,"accept FE "+site.name());
    }
    private static Item item(String key){
        return BuiltInRegistries.ITEM.get(ResourceLocation.parse(key));
    }
    private static MBDMultiblockMachine machine(ServerLevel level,Site site){
        return (MBDMultiblockMachine)IMultiController.ofController(level,site.anchor()).orElseThrow();
    }
    private static BlockState state(ServerLevel level,String block)throws Exception{
        return BlockStateParser.parseForBlock(level.registryAccess().lookupOrThrow(Registries.BLOCK),block,false).blockState();
    }
    private static void require(boolean valid,String message){
        if(!valid)throw new IllegalStateException(message);
    }
}
