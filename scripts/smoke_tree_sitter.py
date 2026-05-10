"""快速冒烟：确认 TreeSitterParser 对主流语言都能抽出函数/类/import。"""
import sys
from pathlib import Path

# 把项目根加入 path，便于从 scripts/ 运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engines.parser import parse_file, supported_languages

print("[Supported]", supported_languages())

SAMPLES = {
    "sample.js": """
// demo
import fs from 'fs';
export class Widget {
  constructor(x) { this.x = x; }
  render() { return this.x; }
}
function hello(name) {
  return `hi ${name}`;
}
""",
    "sample.go": """
package main
import "fmt"
type Greeter struct { name string }
func (g *Greeter) Hello() string { return "hi " + g.name }
func main() { fmt.Println("ok") }
""",
    "sample.rs": """
use std::io;
struct Point { x: i32, y: i32 }
impl Point {
    fn new(x: i32, y: i32) -> Self { Point{x,y} }
}
fn main() { let p = Point::new(1,2); }
""",
    "sample.rb": """
require 'json'
class Foo
  def bar(x)
    x * 2
  end
end
""",
}

for name, src in SAMPLES.items():
    p = Path("_smoke_" + name)
    p.write_text(src, encoding="utf-8")
    try:
        pf = parse_file(p)
        print(f"\n=== {name} / {pf.language} ===")
        print(f"  tokens={len(pf.tokens)}  funcs={len(pf.functions)}  classes={len(pf.classes)}  imports={len(pf.imports)}  err={pf.parse_error}")
        for f in pf.functions:
            print(f"  fn   {f.qualified_name}  L{f.start_line}-{f.end_line}  params={f.parameters}")
        for c in pf.classes:
            print(f"  cls  {c.qualified_name}  L{c.start_line}-{c.end_line}")
        for i in pf.imports:
            print(f"  imp  L{i.line}  {i.module[:60]}")
    finally:
        p.unlink(missing_ok=True)
