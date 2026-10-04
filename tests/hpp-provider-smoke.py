"""Draft-only check with the configured provider; never opens a DB session."""
import asyncio
import importlib.util
import sys
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load("backend.services.unit_utils", "/tmp/hpp_unit_qa.py")
load("backend.services.hpp_math", "/tmp/hpp_math_qa.py")
load("backend.services.hpp_catalog", "/tmp/hpp_catalog_qa.py")
setup = load("backend.services.hpp_setup_service", "/tmp/hpp_setup_qa.py")


async def main():
    story = "Saya mau buat Menu QA nasi. Resep batch 10 porsi: beras mentah 1 kg. Saya beli beras 5 kg Rp75000. Ini data nyata, bukan estimasi."
    output, usage = await setup.generate(None, [SimpleNamespace(message=story, reply=None)], ([], [], []), "manual")
    preview = setup.prepare(output.draft, ([], [], []), [story], "manual")
    assert preview["ready"], preview["missing"]
    assert preview["total_cost"] == "1500.00", preview["total_cost"]
    assert not preview["is_estimated"]
    print("PASS configured provider: manual batch extraction -> backend HPP 1500.00; no DB/stock writes")
    story2 = "Saya ingin buat nasi ayam penyet. Isinya nasi, ayam, tempe dan sambal. Aku bingung takarannya dan harga beli. Tolong estimasikan untuk 10 porsi."
    output, usage = await setup.generate(None, [SimpleNamespace(message=story2, reply=None)], ([], [], []), "estimate")
    preview = setup.prepare(output.draft, ([], [], []), [story2], "estimate")
    assert preview["is_estimated"] and len(preview["lines"]) >= 4
    assert all(line["price_source"] in ("estimate", "unknown") for line in preview["lines"])
    assert any(line["price_source"] == "estimate" for line in preview["lines"])
    print(f"PASS configured provider: estimate -> {len(preview['lines'])} labeled ingredients; ready={preview['ready']}; no DB/stock writes")
    story3 = "Satu porsi tempe goreng memakai 1 potong tempe. Saya beli 2 papan tempe dengan total Rp40000. Masing-masing papan berisi 10 potong tempe. Ini jumlah nyata."
    output, usage = await setup.generate(None, [SimpleNamespace(message=story3, reply=None)], ([], [], []), "manual")
    preview = setup.prepare(output.draft, ([], [], []), [story3], "manual")
    assert preview["ready"], preview["missing"]
    assert preview["total_cost"] == "2000.00", preview["total_cost"]
    assert not preview["is_estimated"]
    print("PASS configured provider: explicit pack contents -> backend 2 × 10 = 20 potong, HPP 2000.00; no DB/stock writes")
    story4 = "Satu porsi nasi memakai beras mentah 100 gram. Saya beli 5 kg beras, harga Rp15000 per kg. Semua data nyata."
    output, usage = await setup.generate(None, [SimpleNamespace(message=story4, reply=None)], ([], [], []), "manual")
    preview = setup.prepare(output.draft, ([], [], []), [story4], "manual")
    assert preview["ready"], {"missing": preview["missing"], "draft": output.draft.model_dump(mode="json")}
    assert preview["total_cost"] == "1500.00", preview["total_cost"]
    assert preview["lines"][0]["buy_price"] == "75000", preview["lines"][0]["buy_price"]
    assert not preview["is_estimated"]
    print("PASS configured provider: original price per kg -> backend purchase total 75000 and HPP 1500.00; no DB/stock writes")


asyncio.run(main())
