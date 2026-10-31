package expedition.ponder;

import com.google.gson.GsonBuilder;
import com.p1nero.iss_ponder.client.ClientPreviewController;
import expedition.ponderui.*;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.registries.ItemRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import net.createmod.catnip.gui.ScreenOpener;
import net.createmod.catnip.layout.PaginationState;
import net.createmod.ponder.foundation.PonderIndex;
import net.createmod.ponder.foundation.ui.*;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.fml.ModList;
import mezz.jei.common.Internal;
import mezz.jei.api.recipe.RecipeType;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Disposable end-to-end exercise of the native Ponder school/spell hierarchy. */
public final class PonderUiProbe {
    private static int ticks,phase,elapsed,initialWidth;
    private static boolean requestScale,appliedScale,done;
    private static ResourceLocation selected,schoolTag;
    private static final List<Map<String,Object>> CHECKS=new ArrayList<>();
    private static final List<String> ERRORS=new ArrayList<>();
    private static volatile int sessions=-1;
    private static int jemmCategories;
    private PonderUiProbe() {}
    public static boolean scaleRequested() {return requestScale && !appliedScale;}
    public static void scaleApplied() {appliedScale=true;}
    private static Object field(Object owner,String name) throws Exception {
        Class<?> type=owner.getClass();
        while(type!=null) {
            try {Field field=type.getDeclaredField(name);field.setAccessible(true);return field.get(owner);}
            catch(NoSuchFieldException e) {type=type.getSuperclass();}
        }
        throw new NoSuchFieldException(name);
    }
    private static void write(String name,Object value) throws Exception {
        Path path=Path.of("kubejs/exported",name);Files.createDirectories(path.getParent());
        Files.writeString(path,new GsonBuilder().setPrettyPrinting().create().toJson(value)+"\n");
    }
    private static void check(String name,boolean passed,Object detail) {
        CHECKS.add(Map.of("check",name,"passed",passed,"detail",String.valueOf(detail)));
        if(!passed)ERRORS.add(name+": "+detail);
    }
    private static void shot(Minecraft client,String name) {Screenshot.m_92295_(client.f_91069_,name+".png",client.m_91385_(),ignored->{});}
    private static boolean preview(Screen screen) {return screen!=null && screen.getClass().getName().endsWith(".SpellPreviewScreen");}
    private static int panelWidth(Screen screen) throws Exception {
        var method=screen.getClass().getDeclaredMethod("panelWidth");method.setAccessible(true);return (Integer)method.invoke(screen);
    }
    private static void next() {phase++;elapsed=0;}
    private static void click(Screen screen,PonderButton button) {screen.m_6375_(button.m_252754_()+6,button.m_252907_()+6,0);}
    private static PonderButton schoolButton(Screen screen) {
        return screen.m_6702_().stream().filter(PonderButton.class::isInstance).map(PonderButton.class::cast)
            .filter(b->b.getTag()!=null && b.getTag().getId().equals(schoolTag)).findFirst().orElseThrow();
    }
    private static PonderButton pager(Screen screen,boolean forward) {
        return screen.m_6702_().stream().filter(PonderButton.class::isInstance).map(PonderButton.class::cast)
            .filter(b->b.m_252907_()==screen.f_96544_-32 && b.m_252754_()==screen.f_96543_/2+(forward?40:-60)).findFirst().orElseThrow();
    }
    private static void playback(Screen screen) throws Exception {
        int x=screen.f_96543_-panelWidth(screen)+15,close=screen.f_96543_-48;
        screen.m_6375_(x+Math.max(40,close-x-7)/2,screen.f_96544_-37,0);
    }
    private static void close(Screen screen) {screen.m_6375_(screen.f_96543_-37,screen.f_96544_-37,0);}
    private static void exposeGlobalSchool(Screen screen) throws Exception {
        List<?> entries=(List<?>)field(screen,"sortedModTags");int index=-1;
        for(int i=0;i<entries.size();i++)if(((Map.Entry<?,?>)entries.get(i)).getKey().equals("iss_ponder")){index=i;break;}
        check("schools listed in global native index",index>=0,entries.size());
        var pagination=(PaginationState)field(screen,"paginationState");
        int page=index/Math.max(1,pagination.getElementsPerPage());
        while(pagination.getPageIndex()<page)pagination.nextPage();
        var setup=PonderTagIndexScreen.class.getDeclaredMethod("setupModTagEntries");setup.setAccessible(true);setup.invoke(screen);
    }
    public static void tick() {
        Minecraft client=Minecraft.m_91087_();
        if(done || client.f_91074_==null || client.f_91073_==null || client.m_91092_()==null)return;
        if(++ticks<160)return;
        try {
            elapsed++;Screen screen=client.f_91080_;
            if(elapsed>600)throw new IllegalStateException("UI test phase timed out: "+phase);
            switch(phase) {
                case 0 -> {
                    check("client adapter loaded",ModList.get().isLoaded("expedition_ponder_ui"),"1.0.2");
                    var schools=SpellPonderCatalog.schools();
                    var spells=schools.stream().flatMap(s->s.spells().stream()).map(AbstractSpell::getSpellResource).toList();
                    long enabled=SpellRegistry.getEnabledSpells().stream().filter(s->s!=null && s!=SpellRegistry.none()).count();
                    check("every enabled spell indexed exactly once",spells.size()==enabled && new HashSet<>(spells).size()==enabled,spells.size()+" / "+enabled);
                    check("school categories registered globally",schools.size()>0 && SpellPonderCatalog.tags().size()==schools.size(),schools.size());
                    schoolTag=schools.stream().filter(s->s.spells().stream().anyMatch(spell->spell.getSpellResource().toString().equals("irons_spellbooks:firebolt")))
                        .findFirst().orElseThrow().tagId();
                    boolean scrolls=true,schoolModels=true;
                    Set<Object> models=Collections.newSetFromMap(new IdentityHashMap<>());
                    for(var tag:SpellPonderCatalog.tags()) {
                        var icon=(ItemStack)field(tag,"itemIcon");
                        scrolls &= icon.m_41720_()==ItemRegistry.SCROLL.get();
                        var expected=SpellPonderCatalog.school(tag.getId()).spells().get(0).getSchoolType().getId();
                        schoolModels &= ISpellContainer.isSpellContainer(icon) &&
                            ISpellContainer.get(icon).getSpellAtIndex(0).getSpell().getSchoolType().getId().equals(expected);
                        models.add(client.m_91291_().m_174264_(icon,client.f_91073_,client.f_91074_,0));
                    }
                    check("first level uses scroll icons",scrolls,"all schools");
                    check("scroll NBT matches each school",schoolModels,"native school scroll models, including add-ons");
                    check("school scroll models visually distinct",models.size()==schools.size(),models.size()+" / "+schools.size());
                    check("existing categories retained",PonderIndex.getTagAccess().getListedTags().size()>schools.size(),PonderIndex.getTagAccess().getListedTags().size());
                    check("native school labels translated",SpellPonderCatalog.tags().stream().noneMatch(tag->tag.getTitle().contains(".ponder.")),"dynamic school names");
                    for(String id:List.of("create:shaft","mekanism:sps_casing","quark:chute"))
                        check("existing Ponder scenes: "+id,PonderIndex.getSceneAccess().doScenesExistForId(new ResourceLocation(id)),id);
                    ClientPreviewController.request(new ResourceLocation("irons_spellbooks:electrocute"),1);next();
                }
                case 1 -> {
                    if(!preview(screen) || elapsed<100)return;
                    initialWidth=screen.f_96543_;shot(client,"01-bottom-left-main");
                    check("normal preview renders",true,screen.f_96543_+"x"+screen.f_96544_);
                    screen.m_6375_(26,17,0);
                    check("old top-left picker removed",!((Boolean)field(field(screen,"spellMenu"),"visible")),"old click has no modal");next();
                }
                case 2 -> {
                    if(elapsed==1){playback(screen);check("pause button inset hitbox",!((Boolean)field(screen,"playbackEnabled")),"pause");}
                    if(elapsed==20){playback(screen);check("play button inset hitbox",(Boolean)field(screen,"playbackEnabled"),"play");}
                    if(elapsed==40){screen.m_6375_(30,screen.f_96544_-30,0);next();}
                }
                case 3 -> {
                    if(elapsed<40)return;
                    check("bottom-left opens native school index",screen instanceof SpellSchoolIndexScreen,screen.getClass());
                    shot(client,"02-school-index");click(screen,schoolButton(screen));next();
                }
                case 4 -> {
                    if(elapsed==40) {
                        check("school opens second level",screen instanceof SpellSchoolScreen,screen.getClass());
                        var spells=(SpellSchoolScreen)screen;shot(client,"03-spell-index");
                        check("second level has spell entries",!spells.spellButtons().isEmpty(),spells.spellButtons().size());
                        boolean square=true;
                        for(var button:spells.spellButtons())square &= (Integer)field(button,"f_93618_")==20 && (Integer)field(button,"f_93619_")==20;
                        check("native 20px square components",square,"same PonderButton constructor as native item entries");
                        requestScale=true;
                    }
                    if(appliedScale && elapsed>=100) {
                        var spells=(SpellSchoolScreen)screen;
                        check("compact school requires pagination",SpellPonderCatalog.school(schoolTag).spells().size()>spells.spellPageSize(),spells.spellPageSize());
                        click(screen,pager(screen,true));next();
                    }
                }
                case 5 -> {
                    if(elapsed<30)return;
                    check("native next page",((SpellSchoolScreen)screen).spellPage()==1,((SpellSchoolScreen)screen).spellPage());
                    shot(client,"04-spell-second-page");click(screen,pager(screen,false));next();
                }
                case 6 -> {
                    if(elapsed<30)return;
                    var spells=(SpellSchoolScreen)screen;check("native previous page",spells.spellPage()==0,spells.spellPage());
                    PonderButton chosen=spells.spellButtons().get(0);
                    for(var button:spells.spellButtons())if(((AbstractSpell)field(button,"spell")).getSpellResource().toString().equals("irons_spellbooks:firebolt")){chosen=button;break;}
                    selected=((AbstractSpell)field(chosen,"spell")).getSpellResource();click(screen,chosen);next();
                }
                case 7 -> {
                    if(!preview(screen) || elapsed<120)return;
                    check("index spell opens native preview",selected.equals(field(screen,"spellId")),field(screen,"spellId"));
                    shot(client,"05-index-selected-preview");requestScale=true;next();
                }
                case 8 -> {
                    if(!appliedScale || elapsed<60)return;
                    check("compact GUI layout",screen.f_96543_<initialWidth,screen.f_96543_+"x"+screen.f_96544_);
                    shot(client,"06-compact-main");screen.m_6050_(screen.f_96543_-35,screen.f_96544_/2.0,-10);next();
                }
                case 9 -> {
                    if(elapsed==30){check("parameter scrolling",((Double)field(screen,"panelScroll"))>0,field(screen,"panelScroll"));shot(client,"07-scrolled-parameters");check("native camera drag",screen.m_7979_(100,100,0,160,-40),"rotate");}
                    if(elapsed==60){shot(client,"08-rotated-scene");check("native camera zoom",screen.m_6050_(100,100,1),"zoom");}
                    if(elapsed==90){shot(client,"09-zoomed-scene");close(screen);next();}
                }
                case 10 -> {
                    if(elapsed<30)return;check("inset close button",screen==null,"closed");
                    ClientPreviewController.request(new ResourceLocation("irons_spellbooks:recall"),1);next();
                }
                case 11 -> {
                    if(!preview(screen) || elapsed<100)return;
                    check("information-only disabled state",!((Boolean)field(screen,"simulationAllowed")),"recall");
                    shot(client,"10-information-only");screen.m_7933_(256,0,0);next();
                }
                case 12 -> {
                    if(elapsed<30)return;check("escape closes preview",screen==null,"escape");
                    ScreenOpener.open(null,new PonderTagIndexScreen());next();
                }
                case 13 -> {
                    if(elapsed==40)exposeGlobalSchool(screen);
                    if(elapsed==60){shot(client,"11-global-ponder-index");click(screen,schoolButton(screen));next();}
                }
                case 14 -> {
                    if(elapsed<40)return;
                    check("global native index opens spell page",screen instanceof SpellSchoolScreen,screen.getClass());
                    screen.m_7933_(259,0,0);next();
                }
                case 15 -> {
                    if(elapsed<30)return;
                    check("native index back navigation",screen!=null && screen.getClass()==PonderTagIndexScreen.class,screen==null?"closed":screen.getClass());
                    client.m_91152_(null);ScreenOpener.clearStack();
                    client.m_91092_().execute(()->{
                        try {Class<?> type=Class.forName("com.p1nero.iss_ponder.server.PreviewSessionManager");Field f=type.getDeclaredField("SESSIONS");f.setAccessible(true);sessions=((Map<?,?>)f.get(null)).size();}
                        catch(Exception e){sessions=-2;}
                    });next();
                }
                case 16 -> {
                    if(elapsed<60)return;check("no preview sessions left",sessions==0,sessions);
                    check("JEMM loaded",ModList.get().isLoaded("jei_mekanism_multiblocks"),"4.27");
                    var runtime=Internal.getJeiRuntime();
                    var categories=runtime.getRecipeManager().createRecipeCategoryLookup().get()
                        .filter(category->category.getRecipeType().getUid().m_135827_().equals("jei_mekanism_multiblocks")).toList();
                    jemmCategories=categories.size();check("JEMM multiblock categories registered",jemmCategories>=9,jemmCategories);
                    boolean recipes=true;
                    for(var category:categories)recipes &= runtime.getRecipeManager().createRecipeLookup(category.getRecipeType()).get().findAny().isPresent();
                    check("JEMM categories have recipes",recipes,jemmCategories);
                    RecipeType<?> tank=categories.stream().filter(c->c.getClass().getSimpleName().contains("DynamicTank")).findFirst().orElseThrow().getRecipeType();
                    runtime.getRecipesGui().showTypes(List.of(tank));next();
                }
                case 17 -> {
                    if(elapsed<60)return;
                    check("JEMM calculator GUI opens",screen!=null && screen.getClass().getName().contains("RecipesGui"),screen==null?"closed":screen.getClass());
                    shot(client,"12-jemm-dynamic-tank");screen.m_7933_(256,0,0);next();
                }
                case 18 -> {
                    if(elapsed<30)return;
                    write("ponder-ui-result.json",Map.of("passed",ERRORS.isEmpty(),"checks",CHECKS,"errors",ERRORS,"sessionsAfterClose",sessions,
                        "schoolCount",SpellPonderCatalog.schools().size(),"indexedSpells",SpellPonderCatalog.schools().stream().mapToInt(s->s.spells().size()).sum(),
                        "jemmCategoryCount",jemmCategories));
                    done=true;client.m_91394_();
                }
            }
            if(ticks%20==0)write("ponder-ui-status.json",Map.of("phase",phase,"elapsed",elapsed,"checks",CHECKS,"errors",ERRORS));
        }catch(Throwable e) {
            e.printStackTrace();ERRORS.add(e.toString());done=true;
            try {write("ponder-ui-result.json",Map.of("passed",false,"phase",phase,"checks",CHECKS,"errors",ERRORS));}catch(Exception ignored){}
            client.m_91152_(null);client.m_91394_();
        }
    }
}
