from app.services.ai.tools.creative.image_gen_tools import generate_image
from app.config.config_manager import config_manager
import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_image_generation():
    """Test image generation with different prompts and parameters"""
    
    # 测试用例列表
    test_cases = [
        {
            "prompt": "professional product photo of wireless earbuds on pure white background, studio lighting, high-end commercial photography",
            "aspect_ratio": "1:1",
            "num_outputs": 1
        },
        {
            "prompt": "lifestyle photo of earbuds being used in a modern coffee shop, soft natural lighting, shallow depth of field",
            "aspect_ratio": "16:9",
            "num_outputs": 1
        }
    ]
    
    for case in test_cases:
        try:
            logger.info(f"Testing image generation with parameters: {case}")
            
            # 生成图片
            input_params = {
                "prompt": case["prompt"],
                "aspect_ratio": case["aspect_ratio"],
                "num_outputs": case["num_outputs"]
            }
            results = await generate_image.ainvoke(input=input_params)
            
            # 验证结果
            logger.info(f"Generation successful!")
            logger.info(f"Number of images generated: {len(results)}")
            logger.info(f"Image URLs: {results}")
            logger.info("-" * 50)
            
        except Exception as e:
            logger.error(f"Error during image generation: {str(e)}")
            raise

async def main():
    """Main test function"""
    try:
        logger.info("Starting image generation tests...")
        await test_image_generation()
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
