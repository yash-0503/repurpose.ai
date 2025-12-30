
def convert_text_to_md(text: str, output_path="downloads/generated_blog.md"):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    with open("downloads/generated_blog.txt", "r", encoding="utf-8") as f:
        blog_text = f.read()

    convert_text_to_md(blog_text)

    with open("downloads/generated_blog.md", "r", encoding="utf-8") as f:
        print(f.read())
