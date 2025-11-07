#!/usr/bin/env python
"""
Custom 🎨 Dream Category Prompts for Dream MCP Server
AI-powered image generation and manipulation for creative visual content
"""

from core.logging import get_logger

logger = get_logger(__name__)

def register_dream_prompts(mcp):
    """Register Dream 🎨 category prompts with the MCP server"""
    
    @mcp.prompt("text_to_image_prompt")
    async def text_to_image_prompt(
        prompt: str = "",
        style_preset: str = "photorealistic",
        quality: str = "high"
    ) -> str:
        """
        Generate a prompt for text-to-image generation with professional photography quality
        
        This prompt creates high-quality photorealistic images from text descriptions
        with professional camera settings and composition.
        
        Args:
            prompt: The main image description
            style_preset: Visual style (photorealistic, artistic, cinematic)
            quality: Image quality level (high, ultra, standard)
        
        Keywords: text-to-image, photography, professional, realistic, creative
        Category: dream
        """
        
        prompt_template = f"""
# Professional Image Generation Expert

## Image Request
**Description**: "{prompt}"
**Style**: {style_preset} aesthetic
**Quality**: {quality} resolution

## Generation Specifications
{prompt}, professional photography, shot on Canon EOS R5 with 85mm f/1.4 lens, {style_preset} aesthetic, natural lighting with soft shadows, {quality} resolution 8K ultra-detailed, hyper-realistic textures, perfect composition following rule of thirds, vibrant yet natural colors with excellent color grading, cinematic depth of field with beautiful bokeh, HDR processing, photorealistic skin texture and fabric details, volumetric lighting creating atmospheric depth, sharp focus on subject with natural background blur, professional retouching maintaining authenticity, award-winning photography style, trending on photography forums, masterpiece quality with film grain texture, natural imperfections for authenticity, captured during golden hour for optimal lighting conditions

## Template Variables
- prompt: {prompt}
- style_preset: {style_preset}
- quality: {quality}

Generate a professional-quality image that meets these specifications.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("image_to_image_prompt")
    async def image_to_image_prompt(
        prompt: str = "",
        style_preset: str = "enhanced",
        strength: str = "medium"
    ) -> str:
        """
        Generate a prompt for image-to-image transformation while preserving composition
        
        This prompt transforms existing images while maintaining original composition
        and key features with enhanced visual quality.
        
        Args:
            prompt: The transformation description
            style_preset: Transformation style (enhanced, artistic, dramatic)
            strength: Transformation intensity (light, medium, strong)
        
        Keywords: image-to-image, transformation, enhancement, composition, style
        Category: dream
        """
        
        prompt_template = f"""
# Image Transformation Specialist

## Transformation Request
**Description**: "{prompt}"
**Style**: {style_preset} transformation
**Intensity**: {strength} strength

## Transformation Specifications
Transform this image: {prompt}, maintaining the original composition and subject while applying {style_preset} transformation, shot with professional DSLR camera settings, enhanced lighting with dramatic shadows and highlights, {strength} transformation intensity preserving key facial features and important details, improved color grading with cinematic tones, enhanced texture definition and surface details, natural skin tone preservation with subtle imperfections, atmospheric depth with volumetric lighting effects, professional post-processing with HDR enhancement, sharp focus maintained throughout transformation, background elements subtly enhanced without losing original context, lighting consistency across all surfaces, natural shadow patterns preserved, enhanced contrast and saturation while maintaining realism, film grain texture for authentic photography feel, detailed fabric textures and material properties clearly defined

## Template Variables
- prompt: {prompt}
- style_preset: {style_preset}
- strength: {strength}

Transform the image while preserving its core composition and identity.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("style_transfer_prompt")
    async def style_transfer_prompt(
        prompt: str = "",
        style_preset: str = "impressionist",
        strength: str = "medium"
    ) -> str:
        """
        Generate a prompt for artistic style transfer with authentic art movement characteristics
        
        This prompt applies artistic styles from famous art movements while preserving
        the original subject matter and composition.
        
        Args:
            prompt: The artistic style description
            style_preset: Art movement style (impressionist, renaissance, abstract)
            strength: Style application intensity (subtle, medium, strong)
        
        Keywords: style-transfer, artistic, art-movement, painting, creative
        Category: dream
        """
        
        prompt_template = f"""
# Artistic Style Transfer Master

## Style Application Request
**Style**: "{prompt}"
**Art Movement**: {style_preset}
**Application Intensity**: {strength}

## Style Transfer Specifications
Apply {prompt} artistic style to this image, {style_preset} art movement characteristics with authentic brushwork techniques, {strength} style application intensity while preserving original subject composition, masterpiece quality artwork with museum-grade execution, rich color palette with period-appropriate pigments and tones, authentic artistic medium simulation including canvas texture and paint application patterns, dramatic lighting effects with chiaroscuro techniques, detailed brushstroke patterns visible at high resolution, professional art reproduction quality with archival color accuracy, enhanced contrast and tonal range for artistic impact, atmospheric perspective with depth and spatial relationships, signature artistic elements including texture, line quality, and compositional balance, fine art print quality with gallery-worthy presentation, historical accuracy in technique and aesthetic approach, enhanced artistic details while maintaining photographic source integrity

## Template Variables
- prompt: {prompt}
- style_preset: {style_preset}
- strength: {strength}

Create an artistic masterpiece while honoring the original composition.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("face_swap_prompt")
    async def face_swap_prompt(
        hair_source: str = "preserve",
        quality: str = "professional"
    ) -> str:
        """
        Generate a prompt for seamless face swapping with natural blending
        
        This prompt enables high-quality face swapping while maintaining
        natural appearance and lighting consistency.
        
        Args:
            hair_source: Hair handling (preserve, adapt, blend)
            quality: Output quality (professional, standard, high)
        
        Keywords: face-swap, portrait, blending, natural, seamless
        Category: dream
        """
        
        prompt_template = f"""
# Professional Face Swap Specialist

## Face Swap Request
**Hair Treatment**: {hair_source}
**Quality Level**: {quality}

## Face Swap Specifications
Seamlessly swap face from source image onto target image body, natural skin tone blending with realistic color matching, {hair_source} hair styling preservation maintaining original texture and flow, professional {quality} face integration with perfect lighting harmonization, smooth facial feature mapping with accurate proportions and geometry, realistic expression matching the target body language and pose, advanced blending algorithms for invisible seam integration, natural shadow and highlight preservation across facial contours, authentic skin texture continuity with pore detail and natural imperfections, professional photo editing quality with magazine-grade retouching, consistent lighting direction and color temperature throughout, natural edge blending where face meets hair and neck, preserved facial identity characteristics while adapting to new environment, high-resolution output maintaining source face detail clarity, photorealistic result indistinguishable from original photography

## Template Variables
- hair_source: {hair_source}
- quality: {quality}

Create a seamless face swap that looks completely natural.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("professional_headshot_prompt")
    async def professional_headshot_prompt(
        prompt: str = "",
        industry: str = "corporate",
        quality: str = "executive"
    ) -> str:
        """
        Generate a prompt for professional business headshot transformation
        
        This prompt transforms casual photos into professional business headshots
        suitable for LinkedIn and corporate use.
        
        Args:
            prompt: The headshot description
            industry: Industry context (corporate, creative, tech, healthcare)
            quality: Professional level (executive, standard, premium)
        
        Keywords: headshot, professional, business, corporate, LinkedIn
        Category: dream
        """
        
        prompt_template = f"""
# Professional Headshot Photographer

## Headshot Request
**Description**: "{prompt}"
**Industry**: {industry}
**Quality Level**: {quality}

## Professional Headshot Specifications
Transform casual photo into professional business headshot: {prompt}, {industry} industry-appropriate styling with executive-level presentation, professional studio lighting with soft key light and subtle fill, clean neutral background in corporate gray or white, formal business attire including tailored suit jacket and professional shirt, confident approachable expression balancing authority with accessibility, {quality} retouching with natural skin enhancement preserving authentic appearance, sharp focus on eyes with professional catchlight, shallow depth of field isolating subject from background, corporate color grading with professional tone mapping, LinkedIn-ready composition following business photography standards, executive presence with proper posture and professional bearing, high-resolution 8K quality suitable for print and digital business applications, magazine-quality professional photography with commercial lighting setup, natural makeup and grooming for polished business appearance

## Template Variables
- prompt: {prompt}
- industry: {industry}
- quality: {quality}

Create a professional headshot that commands respect and trust.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("emoji_generation_prompt")
    async def emoji_generation_prompt(
        prompt: str = "",
        expression: str = "happy",
        style_preset: str = "kawaii",
        color_scheme: str = "vibrant"
    ) -> str:
        """
        Generate a prompt for custom emoji creation with scalable design
        
        This prompt creates custom emojis with clear features optimized
        for digital platforms and social media use.
        
        Args:
            prompt: The emoji description
            expression: Emotional expression (happy, sad, excited, surprised)
            style_preset: Design style (kawaii, modern, classic, minimal)
            color_scheme: Color palette (vibrant, pastel, monochrome, rainbow)
        
        Keywords: emoji, sticker, cute, scalable, social-media
        Category: dream
        """
        
        prompt_template = f"""
# Custom Emoji Designer

## Emoji Creation Request
**Description**: "{prompt}"
**Expression**: {expression}
**Style**: {style_preset}
**Colors**: {color_scheme}

## Emoji Generation Specifications
Create custom emoji: {prompt}, {expression} emotional expression with clear readable features at small sizes, {style_preset} design approach with platform-optimized aesthetics, {color_scheme} color palette with high contrast and vibrant saturation, bold black outlines for definition and clarity, simple geometric shapes minimizing complex details, expressive oversized eyes with emotional sparkle and personality, rounded friendly proportions with kawaii influence, universal cultural recognition for global communication, scalable vector design maintaining clarity from 16px to 128px display sizes, social media platform compatibility with transparent background, memorable visual impact with instant emotional communication, smooth gradient fills and clean line work, professional emoji quality matching platform standards, cheerful and engaging character design with positive emotional resonance, trending digital expression style with modern aesthetic appeal

## Template Variables
- prompt: {prompt}
- expression: {expression}
- style_preset: {style_preset}
- color_scheme: {color_scheme}

Design an emoji that communicates emotion instantly and universally.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("photo_inpainting_prompt")
    async def photo_inpainting_prompt(
        prompt: str = "",
        fill_method: str = "content_aware",
        strength: str = "seamless"
    ) -> str:
        """
        Generate a prompt for photo inpainting and object removal
        
        This prompt removes unwanted elements from photos with seamless
        texture synthesis and natural blending.
        
        Args:
            prompt: The inpainting description
            fill_method: Filling technique (content_aware, texture_synthesis, smart_fill)
            strength: Blending intensity (seamless, natural, enhanced)
        
        Keywords: inpainting, removal, restoration, seamless, healing
        Category: dream
        """
        
        prompt_template = f"""
# Photo Restoration and Inpainting Expert

## Inpainting Request
**Task**: "{prompt}"
**Method**: {fill_method}
**Quality**: {strength}

## Photo Inpainting Specifications
Remove unwanted elements: {prompt}, seamless object removal with professional photo restoration quality, {fill_method} intelligent filling matching surrounding textures and patterns, {strength} modification intensity preserving natural image integrity, advanced content-aware healing with realistic texture synthesis, perfect lighting continuity across inpainted areas, natural shadow and highlight reconstruction, authentic surface material matching including grain, color, and pattern consistency, invisible seam blending with surrounding context, professional retouching maintaining photographic authenticity, enhanced detail reconstruction in filled areas, consistent perspective and spatial relationships, natural wear patterns and aging effects where appropriate, high-resolution texture synthesis matching original image quality, realistic environmental context preservation, museum-quality photo restoration with archival standards

## Template Variables
- prompt: {prompt}
- fill_method: {fill_method}
- strength: {strength}

Restore the photo with invisible, professional-quality inpainting.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("photo_outpainting_prompt")
    async def photo_outpainting_prompt(
        prompt: str = "",
        direction: str = "all_sides",
        strength: str = "natural"
    ) -> str:
        """
        Generate a prompt for photo outpainting and boundary expansion
        
        This prompt expands image boundaries with natural scene continuation
        and environmental logic while maintaining perspective.
        
        Args:
            prompt: The outpainting description
            direction: Expansion direction (all_sides, horizontal, vertical, specific)
            strength: Expansion intensity (natural, enhanced, dramatic)
        
        Keywords: outpainting, expansion, panoramic, scene-extension, perspective
        Category: dream
        """
        
        prompt_template = f"""
# Photo Outpainting and Scene Extension Specialist

## Outpainting Request
**Task**: "{prompt}"
**Direction**: {direction}
**Quality**: {strength}

## Photo Outpainting Specifications
Expand image boundaries: {prompt}, {direction} extension with natural scene continuation and environmental logic, {strength} expansion intensity maintaining perspective accuracy and spatial relationships, seamless blending between original and extended areas with invisible transition zones, authentic environmental elements following natural or architectural patterns, consistent lighting direction and atmospheric conditions throughout expansion, realistic texture continuation matching original surface materials and weathering, proper perspective maintenance with accurate vanishing points and scale relationships, natural color grading consistency across original and extended regions, enhanced compositional balance with improved visual flow, professional landscape extension quality with panoramic photography standards, detailed background elements with appropriate depth and focus, realistic shadow patterns and highlight distribution, authentic environmental storytelling with logical scene progression, high-resolution detail synthesis maintaining original image sharpness and clarity

## Template Variables
- prompt: {prompt}
- direction: {direction}
- strength: {strength}

Expand the scene naturally while maintaining photographic integrity.
"""
        
        return prompt_template.strip()
    
    @mcp.prompt("sticker_generation_prompt")
    async def sticker_generation_prompt(
        prompt: str = "",
        style_preset: str = "kawaii",
        theme: str = "cute_animal"
    ) -> str:
        """
        Generate a prompt for cute sticker design creation
        
        This prompt creates adorable sticker designs optimized for digital
        platforms with scalable vector graphics and universal appeal.
        
        Args:
            prompt: The sticker description
            style_preset: Design style (kawaii, chibi, modern, vintage)
            theme: Sticker theme (cute_animal, food, nature, emoji)
        
        Keywords: sticker, cute, kawaii, scalable, digital, social-media
        Category: dream
        """
        
        prompt_template = f"""
# Cute Sticker Design Artist

## Sticker Creation Request
**Description**: "{prompt}"
**Style**: {style_preset}
**Theme**: {theme}

## Sticker Generation Specifications
Create cute sticker design: {prompt}, {style_preset} kawaii aesthetic with adorable character features, vibrant bright colors with high contrast for visibility at small sizes, thick black outlines for definition and clarity, simple geometric shapes with minimal detail complexity, expressive large eyes with sparkles and emotion, rounded soft edges and friendly proportions, {theme} themed elements with appropriate symbols and motifs, cheerful and positive emotional expression, bold saturated color palette optimized for digital platforms, clean vector-style illustration with smooth gradients, scalable design maintaining clarity from 16px to 512px, universal appeal with cross-cultural recognition, professional sticker quality with transparent background, social media ready format, trending cute character design, memorable visual impact with instant emotional connection

## Template Variables
- prompt: {prompt}
- style_preset: {style_preset}
- theme: {theme}

Design an irresistibly cute sticker that spreads joy and positivity.
"""
        
        return prompt_template.strip()

    logger.info("Dream 🎨 prompts registered successfully")

# For compatibility with auto-discovery  
def register_prompts(mcp):
    """Legacy function name for auto-discovery"""
    register_dream_prompts(mcp)