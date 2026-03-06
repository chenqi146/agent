# 只运行并发测试
python vlm_test.py --concurrent-only

# 指定并发线程数
python vlm_test.py --concurrent-only --concurrent-threads 5

# 正常运行所有测试（包含并发测试）
python vlm_test.py

# 只运行流式测试（所有模式）
python vlm_test.py --stream-only

# 只测试 Token 模式
python vlm_test.py --stream-only --stream-mode token

# 只测试 Chunk 模式
python vlm_test.py --stream-only --stream-mode chunk

# 只测试 Auto 模式
python vlm_test.py --stream-only --stream-mode auto

# 运行所有测试（包含流式测试）
python vlm_test.py

# 备注
token与chunk测试用例只能二选一