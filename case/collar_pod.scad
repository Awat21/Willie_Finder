// Willie Finder - collar pod, form-factor study (v0)
// Fits: RAK19003 mini base + RAK4631 core + RAK12500 GPS, 250 mAh LiPo (502030),
// 15 mm ceramic GPS patch antenna on top of the battery.
// Two flat bays joined at an angle so the pod follows the neck instead of standing off it.
// All dimensions in mm. Values marked ASSUMED must be checked against real parts.

part = "assembly"; // base | lid | board | battery | gps | strap | antenna | assembly

// ---- electronics envelope ----
board_l = 35;      // RAK19003 outline
board_w = 30;
stack_h = 9.5;     // ASSUMED: base + core on top + GPS module underneath
batt_l  = 20;      // 502030 LiPo laid across the pod
batt_w  = 30;
batt_h  = 5;
patch   = 15;      // GPS patch antenna, 15 x 15 x 4
patch_h = 4;

// ---- case ----
clr   = 0.5;       // clearance around parts
wall  = 1.6;
floor = 1.4;
roof  = 1.4;
bend  = 32;        // angle between the two bays (suits ~50 mm neck radius incl. fur)
rr    = 3.2;       // outside corner radius
strap_w = 10.5;    // cat collar webbing
strap_t = 1.8;
lug_l = 7;
ant_l = 38;        // adhesive flex antenna on the collar, e.g. Molex 211140-0100 (38 x 10 x 0.1)
ant_w = 10;

in_w = board_w + 2*clr;            // 31
in_h = stack_h + 0.3;              // 9.8
la   = board_l + 2*clr + wall;     // bay A outside length (joint side is open)
lb   = batt_l + 2*clr + wall;      // bay B outside length
W    = in_w + 2*wall;              // 34.2
H    = in_h + floor + roof;        // 12.6
split = floor + 5.2;               // lid/base seam height

$fn = 40;

module rbox(l, w, h, r) {          // rounded box, x from 0..l, y centred, z 0..h
  hull() for (x=[r, l-r], y=[-w/2+r, w/2-r], z=[r, h-r]) translate([x,y,z]) sphere(r);
}
module slice(w, h, r) {            // thin cross-section used to bridge the joint
  hull() for (y=[-w/2+r, w/2-r], z=[r, h-r]) translate([0,y,z]) rotate([0,90,0]) cylinder(r=r, h=0.01);
}
// frame B: hinged about the bottom edge of the joint, end drops toward the neck
module frameB() { rotate([0, bend, 0]) children(); }
module frameA() { mirror([1,0,0]) children(); }   // bay A runs in -x

module lug() {                      // tapered strap lug, doubles as an anti-snag ramp
  difference() {
    hull() {
      translate([-0.1,0,0]) slice(W-4, 6.0, 2.0);
      translate([lug_l,0,0]) slice(strap_w+5, 3.6, 1.7);
    }
    translate([lug_l-3.6, -strap_w/2, -1]) cube([2.2, strap_w, 10]);
  }
}

module outer() {
  frameA() { rbox(la, W, H, rr); translate([la-rr,0,0]) lug(); }
  frameB() { rbox(lb, W, H, rr); translate([lb-rr,0,0]) lug(); }
  hull() { frameA() translate([rr,0,0]) slice(W,H,rr); frameB() translate([rr,0,0]) slice(W,H,rr); }
}
module pocket(l) { translate([0, -in_w/2, floor]) cube([l, in_w, in_h]); }
module inner() {
  frameA() pocket(la - wall);
  frameB() pocket(lb - wall);
  hull() {
    frameA() translate([0,-in_w/2,floor]) cube([0.01,in_w,in_h]);
    frameB() translate([0,-in_w/2,floor]) cube([0.01,in_w,in_h]);
  }
}
module usb_port() {                 // ASSUMED: USB-C on the short edge of the board, facing the pod end
  frameA() translate([la-wall-1, -5, floor+4.6]) cube([wall+6, 10, 4]);
}
module shell() { difference() { outer(); inner(); usb_port(); } }

module upper() {                    // everything above the seam
  frameA() translate([-1,-50,split]) cube([la+20,100,30]);
  frameB() translate([-1,-50,split]) cube([lb+20,100,30]);
  hull() {
    frameA() translate([0,-50,split]) cube([0.01,100,30]);
    frameB() translate([0,-50,split]) cube([0.01,100,30]);
  }
}
module base() { difference() { shell(); upper(); } }
module lid()  { intersection() { shell(); upper(); } }

// ---- mock components ----
module board() frameA() translate([clr, -board_w/2, floor]) {
  translate([0,0,3.0]) color("green") cube([board_l, board_w, 1.0]);          // base PCB
  translate([4,5,4.0]) cube([30, 20, 3.2]);                                   // RAK4631 core
  translate([6,3,0.2]) cube([23, 10, 2.8]);                                   // RAK12500 under
  translate([board_l-7.5,10.5,4.0]) cube([7.5, 9, 3.2]);                      // USB-C
}
module battery() frameB() translate([clr, -batt_w/2, floor+0.2]) cube([batt_l, batt_w, batt_h]);
module gps()     frameB() translate([clr+2.5, -patch/2, floor+0.4+batt_h]) cube([patch, patch, patch_h]);
module strap() {                    // collar webbing passing through both lugs, under the pod
  frameA() translate([-2,-strap_w/2,-strap_t-0.2]) cube([la+lug_l+ant_l+12, strap_w, strap_t]);
  frameB() translate([-2,-strap_w/2,-strap_t-0.2]) cube([lb+lug_l+22, strap_w, strap_t]);
}

module antenna() {                  // stuck to the outer face of the collar, just past the lug
  frameA() translate([la-rr+lug_l+2, -ant_w/2, -0.2]) cube([ant_l, ant_w, 0.3]);
}

if (part=="base") base();
if (part=="antenna") antenna();
if (part=="lid") lid();
if (part=="board") board();
if (part=="battery") battery();
if (part=="gps") gps();
if (part=="strap") strap();
if (part=="assembly") { base(); %lid(); board(); battery(); gps(); strap(); antenna(); }
