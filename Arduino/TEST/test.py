# utf8_encode_test.py

def main():
    # 이름 입력
    name = "김민수"

    # UTF-8 인코딩
    encoded = name.encode('utf-8')

    # 출력
    print("▶ 입력한 이름:", name)
    print("▶ UTF-8 인코딩 (bytes):", encoded)
    print("▶ UTF-8 인코딩 (hex):", encoded.hex())
    print("▶ UTF-8 인코딩 (공백 구분):", ' '.join(f'{b:02x}' for b in encoded))

if __name__ == "__main__":
    main()
