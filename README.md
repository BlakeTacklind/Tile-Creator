# Tile-Creator

This creates a xml to be used in [Fantasy Grounds Unity](https://www.fantasygrounds.com/home/FantasyGroundsUnity.php) from the save file from [Dungeon Painter (Steam)](http://store.steampowered.com/app/592260)

## Usage

Create an image from dungeon painter. Add the image the image to your fantasy grounds assets folder. Save the file from dungeon painter.

run `application.py <input dps> <output xml>`

Add the XML to asset folder. Make sure it have the same name as the image, excepting the extension. IE `Cool Map.png` and `Cool Map.xml`

Now when adding that image to file to a map It should have LOS

## What's a what?

In order for it to work it looks at layer names. Starting a layer with `wall` (which is default) will create a wall LOS. A layer  with `door` in the name will create a door LOS (having `double` in the name will make a double door). A layer that starts with `secret` will create a togglable wall (secret door). All of these things have only had very limited testing.

### Pitfalls

* Walls under doors are still walls. Remove the wall that is directly underneath it or rename it to not start with `wall`
* It's dumb software, something like the layer name `corridoor` has `door` and will try to create a door LOS
* I have occasionally seen the definition somewhat shifted. Use `-x` and `-y` options to fix it in these cases

## Future Work

* Create terrain

