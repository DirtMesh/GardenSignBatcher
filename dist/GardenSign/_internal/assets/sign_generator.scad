// Garden Sign v2

/* [Crop Entry] */
crop_name = "Broccoli";
cultivar  = "Waltham 29";

crop_name_size = 8;
cultivar_size  = 6;

/* [Export] */
export_part = "all"; // [all,a,b]

/* [Hidden] */
color_a = "#FFFFFF"; // preview only
color_b = "#000000"; // preview only

// ---------- Geometry defaults ----------
$fn = 48;
corner_radius = 3;     // mm
text_height   = 0.20;  // mm
text_z_fudge  = 0.01;  // mm

// ---------- Fonts ----------
font_line1  = "Arial:Bold";
font_line2  = "Arial:Bold";

// ---------- Text layout ----------
text_margin_x  = 4.0;  // mm
text_margin_y  = 3.0;  // mm
line2_margin_y = 4.0;  // mm

// Approx glyph width factors (mm per char per "size" unit)
avg_char_width_factor    = 1.00; // line 1
avg_char_width_factor_lc = 0.80; // line 2

// Clearance above slot band before text block starts
slot_to_text_clearance = 2.0; // mm

// ---------- Zip-tie slot geometry ----------
slot_w = 8.0;     // mm (slot length)
slot_h = 3.2;     // mm (slot height)
slot_r = 1.6;     // mm (end radius)
slot_side_margin   = 6.0; // mm
slot_bottom_margin = 3.0; // mm

function clamp(x, lo, hi) = x < lo ? lo : (x > hi ? hi : x);

function to_upper(s, i=0, acc="") =
    i >= len(s)
        ? acc
        : to_upper(
            s,
            i + 1,
            str(
                acc,
                let(c = s[i])
                    (c >= "a" && c <= "z")
                        ? chr(ord(c) - 32)
                        : c
            )
        );

// Compute top width from bottom width, height, and side angle (deg from horizontal)
function dt_top_w(bottom_w, height, side_angle_deg) =
    let(a = clamp(side_angle_deg, 5, 85))
    bottom_w - 2 * height / tan(a);

// 2D trapezoid (centered at origin). bottom width=w0, top width=w1, height=h
module trapezoid_2d(w0, w1, h) {
    polygon(points=[
        [-w0/2, 0],
        [ w0/2, 0],
        [ w1/2, h],
        [-w1/2, h]
    ]);
}

// 2D dovetail rib profile (male). Base on y=0, grows to y=height.
module dovetail_rib_2d(bottom_w=6, height=2.0, side_angle_deg=60) {
    w1 = dt_top_w(bottom_w, height, side_angle_deg);
    if (w1 <= 0) {
        echo("ERROR: dovetail top width <= 0. Reduce height or increase bottom_w or angle.");
    } else {
        trapezoid_2d(bottom_w, w1, height);
    }
}

module dovetail_rib_3d(len=40, bottom_w=6, height=2.0, side_angle_deg=60) {
    linear_extrude(height=len)
        dovetail_rib_2d(bottom_w=bottom_w, height=height, side_angle_deg=side_angle_deg);
}

// Centered rounded rectangle prism (centered at XY origin, centered in Z)
module rounded_rect_prism(size_xyz, r) {
    x = size_xyz[0];
    y = size_xyz[1];
    z = size_xyz[2];

    r_safe = min(r, x/2, y/2);

    translate([0, 0, -z/2])
        linear_extrude(height = z)
            offset(r = r_safe)
                square([x - 2*r_safe, y - 2*r_safe], center = true);
}

// 2D rounded slot (capsule)
module slot2d(w, h, r) {
    rr = min(r, h/2, w/2);
    intersection() {
        hull() {
            translate([-(w/2 - rr), 0]) circle(r = rr);
            translate([ +(w/2 - rr), 0]) circle(r = rr);
        }
        square([w, h], center = true);
    }
}

// 3D through-slot
module slot3d(w, h, r, thickness) {
    translate([0, 0, -thickness/2 - 0.2])
        linear_extrude(height = thickness + 0.4)
            slot2d(w, h, r);
}

// Part A: base and attachments (separate solid for filament A)
module part_a(
    W, H, T,
    slot_x, slot_y,
    dovetail_yshift, dovetail_height, dovetail_len, dovetail_bottom_w, dovetail_angle,
    tabs_xshift, tabs_len, tabs_cap_offset, tabs_bottom_w, tabs_height, tabs_angle,
    cap_width, cap_height
) {
    // Main plate with slots
    difference() {
        rounded_rect_prism([W, H, T], corner_radius);

        for (sx = [-slot_x, +slot_x]) {
            translate([sx, slot_y, 0])
                slot3d(slot_w, slot_h, slot_r, T);
        }
    }

    // Main dovetail rib
    translate([0, dovetail_yshift, -(T/2 + dovetail_height)])
        rotate([90, 0, 0])
            dovetail_rib_3d(
                len = dovetail_len,
                bottom_w = dovetail_bottom_w,
                height = dovetail_height,
                side_angle_deg = dovetail_angle
            );

    // Small tabs
    for (sx = [-tabs_xshift, tabs_xshift + tabs_len]) {
        translate([sx, dovetail_yshift + tabs_cap_offset, -T/2])
            rotate([-90, 0, 90])
                dovetail_rib_3d(
                    len = tabs_len,
                    bottom_w = tabs_bottom_w,
                    height = tabs_height,
                    side_angle_deg = tabs_angle
                );
    }

    // Cap block
    translate([0, dovetail_yshift + cap_height/2, -(dovetail_height/2 + T/2)])
        rounded_rect_prism([cap_width, cap_height, dovetail_height], 0.50);
}

// Part B: raised text only (separate solid for filament B)
module part_b(T, line_1_baseline, line_2_baseline, line_1_size, line_2_size) {
    translate([0, 0, T/2 - text_height + text_z_fudge]) {

        linear_extrude(height = text_height)
            translate([0, line_1_baseline])
                text(
                    to_upper(crop_name),
                    size = line_1_size,
                    font = font_line1,
                    halign = "center",
                    valign = "baseline"
                );

        linear_extrude(height = text_height)
            translate([0, line_2_baseline])
                text(
                    cultivar,
                    size = line_2_size,
                    font = font_line2,
                    halign = "center",
                    valign = "baseline"
                );
    }
}

module mw_plate_1() {

    // Clamp sizes to keep things printable
    line_1_size = max(5, crop_name_size);
    line_2_size = max(4, cultivar_size);

    // --- Size estimates (simple width model) ---
    min_card_width_mm =
        2 * text_margin_x +
        max(
            len(crop_name) * line_1_size * avg_char_width_factor,
            len(cultivar)  * line_2_size * avg_char_width_factor_lc
        );

    W = max(50, min_card_width_mm);

    min_card_height_mm =
        text_margin_y +
        slot_to_text_clearance +
        slot_h/2 +
        slot_bottom_margin +
        line_1_size +
        line2_margin_y +
        line_2_size;

    H = max(25, min_card_height_mm);
    T = 2;

    // --- Dovetail cap ---
    cap_width  = 7;
    cap_height = 2;

    // --- Dovetail params ---
    dovetail_yshift   = 2.5;
    dovetail_bottom_w = 5.0;
    dovetail_height   = 2.6;
    dovetail_angle    = 60;
    dovetail_len      = 10;

    // --- Tabs ---
    tabs_len      = 3;
    tabs_bottom_w = 2;
    tabs_height   = 0.6;
    tabs_angle    = 45;

    tabs_cap_offset = -2.0;
    tabs_xshift     = 10;

    // --- Slot locations ---
    slot_x = (25 - slot_side_margin);
    slot_y = -(H/2) + slot_bottom_margin;

    // --- Text baselines ---
    line_1_baseline = H/2 - text_margin_y - line_1_size;
    line_2_baseline = line_1_baseline - line2_margin_y - line_2_size;

    // Keep a consistent global frame for all exports
    rotate([180, 0, 0]) {
        if (export_part == "a") {

            part_a(
                W, H, T,
                slot_x, slot_y,
                dovetail_yshift, dovetail_height, dovetail_len, dovetail_bottom_w, dovetail_angle,
                tabs_xshift, tabs_len, tabs_cap_offset, tabs_bottom_w, tabs_height, tabs_angle,
                cap_width, cap_height
            );

        } else if (export_part == "b") {

            part_b(T, line_1_baseline, line_2_baseline, line_1_size, line_2_size);

        } else {

            color(color_a)
                part_a(
                    W, H, T,
                    slot_x, slot_y,
                    dovetail_yshift, dovetail_height, dovetail_len, dovetail_bottom_w, dovetail_angle,
                    tabs_xshift, tabs_len, tabs_cap_offset, tabs_bottom_w, tabs_height, tabs_angle,
                    cap_width, cap_height
                );

            color(color_b)
                part_b(T, line_1_baseline, line_2_baseline, line_1_size, line_2_size);
        }
    }
}


module mw_assembly_view() {
    rotate([270,0,0]){
        mw_plate_1();
    }
    
}

mw_plate_1();
