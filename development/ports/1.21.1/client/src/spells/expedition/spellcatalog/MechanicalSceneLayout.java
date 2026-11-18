package expedition.spellcatalog;

import com.mojang.blaze3d.vertex.PoseStack;
import com.p1nero.iss_ponder.client.PreviewProjection;
import expedition.spellcatalog.mixin.PreviewProjectionAccess;
import net.minecraft.client.gui.GuiGraphics;
import org.joml.Vector3f;

/** Fits the complete 7 by 11 platform and standing entities, with no scene scissor. */
public final class MechanicalSceneLayout {
    private MechanicalSceneLayout() {}
    public static void render(GuiGraphics graphics,int width,int height,float partialTick) {
        var scene=PreviewProjectionAccess.expedition$scene();
        if(scene==null) {PreviewProjection.render(graphics,width,height,partialTick);return;}
        var transform=scene.getTransform();
        transform.updateScreenParams(0,0,0);
        PoseStack boundsPose=new PoseStack();
        transform.apply(boundsPose,partialTick);
        var matrix=boundsPose.last().pose();
        float minX=Float.POSITIVE_INFINITY,minY=minX,maxX=Float.NEGATIVE_INFINITY,maxY=maxX;
        for(float x:new float[]{-3,4}) for(float y:new float[]{0,3.5F}) for(float z:new float[]{-5,6}) {
            var point=matrix.transformPosition(new Vector3f(x,y,z));
            minX=Math.min(minX,point.x);maxX=Math.max(maxX,point.x);
            minY=Math.min(minY,point.y);maxY=Math.max(maxY,point.y);
        }
        // Fit at the default zoom; native wheel zoom remains free to magnify the scene.
        float baseRatio=0.82F/Math.max(0.01F,PreviewProjectionAccess.expedition$zoom());
        float scale=Math.min(1,Math.min((width-28)/Math.max(1,(maxX-minX)*baseRatio),
            (height-70)/Math.max(1,(maxY-minY)*baseRatio)));
        PoseStack pose=graphics.pose();pose.pushPose();
        try {
            pose.translate(width/2F,(height-46)/2F,0);
            pose.scale(scale,scale,1);
            pose.translate(-width/2F-(minX+maxX)/2,-height/2F-(minY+maxY)/2,0);
            PreviewProjection.render(graphics,width,height,partialTick);
        } finally {pose.popPose();}
    }
}
